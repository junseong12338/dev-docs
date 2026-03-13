# LMS Redis 중복 체크 메커니즘 - 정확 분석

**작성일**: 2025-12-17
**대상**: 개발자 (중급 이상)
**난이도**: ★★★★☆
**기반**: 실제 코드 분석 결과

---

## 목차
1. [핵심 요약](#1-핵심-요약)
2. [Redis 키 구조](#2-redis-키-구조)
3. [EventId 구조](#3-eventid-구조)
4. [중복 학습 체크 - 완전 분석](#4-중복-학습-체크---완전-분석)
5. [중복 시험 체크 - 완전 분석](#5-중복-시험-체크---완전-분석)
6. [다중 WAS 환경 동작 원리](#6-다중-was-환경-동작-원리)
7. [실제 시나리오별 동작](#7-실제-시나리오별-동작)
8. [관련 파일 목록](#8-관련-파일-목록)

---

## 1. 핵심 요약

### 1.1 한 줄 정리

> **Redis는 "세션 전체"가 아닌 "활성 세션 식별자(eventId)"만 저장하고, Pub/Sub으로 모든 WAS에 동시 알림하여 중복을 감지한다.**

### 1.2 핵심 구조

!!! abstract "LMS 중복 체크 핵심 구조"

    **저장소 분리**

    | 구분 | Redis Hash | WAS 메모리 |
    |------|-----------|-----------|
    | **저장 대상** | eventId 목록 저장 | SseEmitter 저장 |
    | **공유 범위** | 모든 WAS 공유 | 현재 WAS만 보유 |
    | **역할** | 중복 판단 기준 | 실제 연결 객체 |

    **통신 방식**

    | 구분 | Redis Pub/Sub | SSE (Server-Sent Events) |
    |------|--------------|--------------------------|
    | **방향** | WAS 간 통신 | WAS → 브라우저 |
    | **용도** | 이벤트 전파 | 실시간 알림 |

### 1.3 중복 판단 로직 (핵심)

!!! danger "중복 판단 핵심 로직"

    **중복 판단 = Redis Hash에 같은 사용자의 다른 eventId가 있는가?**

    ```
    Redis Hash: KNU10-LMS:lesson:USER123
    {
      "USER123:20251217:abc:LESSON001": emitter1  ← PC
      "USER123:20251217:def:LESSON001": emitter2  ← 모바일
    }

    → 2개 존재 = 중복!
    → 기존 세션(abc)에 "conflict" 이벤트 전송
    ```

---

## 2. Redis 키 구조

### 2.1 키 생성 규칙

**코드 위치**: `LessonRedisComponent.java:177-179`

```java
public String parseKey(String key) {
    return String.format("%s:%s:%s", REDIS_SITE, MODULE_NAME, key);
}
```

### 2.2 실제 키 형식

!!! info "Redis 키 구조"

    **형식**: `{REDIS_SITE}:{MODULE_NAME}:{USER_NO}`

    | REDIS_SITE | MODULE_NAME | USER_NO (키) |
    |-----------|------------|-------------|
    | KNU10-LMS | lesson | USER123 |
    | KNU10-LMS | exam | USER123 |

    **실제 예시:**

    - `KNU10-LMS:lesson:USER123` -- 학습 중복 체크용
    - `KNU10-LMS:exam:USER123` -- 시험 중복 체크용

### 2.3 Redis 데이터 타입: Hash

!!! note "Redis Hash 구조"

    - **KEY**: `KNU10-LMS:lesson:USER123`
    - **TYPE**: Hash
    - **TTL**: 86400초 (24시간)

    **FIELDS (Hash 내부):**

    | Hash Field (eventId) | Hash Value |
    |---------------------|-----------|
    | USER123:20251217:abc123:LESSON001 | [SseEmitter] |
    | USER123:20251217:def456:LESSON001 | [SseEmitter] |

    !!! warning "주의"
        Hash Value의 SseEmitter는 직렬화 불가하므로 실제로는 WAS 메모리의 CLIENTS Map에서 관리합니다. Redis Hash는 **"어떤 eventId가 활성 상태인지"만 저장**합니다.

---

## 3. EventId 구조

### 3.1 EventId 형식

**코드 위치**: `LessonSseService.java:56`, `ExamSseService.java:56`

```java
// USER_NO, date, ranVal, lessonCntsId (또는 contentsType)
String[] dataArr = eventId.split(":");
String userNo = dataArr[0];
```

### 3.2 EventId 구성요소

!!! info "EventId 구조 분석"

    **형식**: `{USER_NO}:{날짜}:{랜덤값}:{콘텐츠ID/타입}`

    | dataArr[0] | dataArr[1] | dataArr[2] | dataArr[3] |
    |-----------|-----------|-----------|-----------|
    | USER_NO | 날짜 | 랜덤값 | 콘텐츠ID/타입 |
    | USER123 | 20251217 | abc123 | LESSON001 |
    | USER123 | 20251217 | def456 | EXAM |

    **실제 예시:**

    - `USER123:20251217:abc123:LESSON001` -- 학습 세션
    - `USER123:20251217:def456:EXAM` -- 시험 세션

    ※ 랜덤값으로 같은 사용자의 여러 세션 구분

---

## 4. 중복 학습 체크 - 완전 분석

### 4.1 전체 흐름도

!!! example "중복 학습 체크 전체 흐름"

    **Step 1. 학습 시작 - 이벤트 생성**

    ```mermaid
    graph LR
        A["브라우저"] -->|"GET /lesson/sse/{eventId}"| B["LessonSseController"]
        B --> C["LessonSseService.createEvent()"]
        C --> D["Redis Hash 저장<br>(eventId 등록)"]
        C --> E["WAS 메모리 저장<br>(SseEmitter)"]
    ```

    **Step 2. 중복 체크 요청**

    ```mermaid
    graph LR
        A["브라우저"] -->|"GET .../handler/DUPLICATE_LEARNING_CHECK"| B["LessonSseController"]
        B --> C["LessonSseService.publishMessage()"]
        C --> D["Redis Pub/Sub 채널로 발행"]
    ```

    **Step 3. 모든 WAS에서 메시지 수신**

    ```mermaid
    graph TD
        A["Redis Pub/Sub"] --> B["WAS 01<br>Subscriber"]
        A --> C["WAS 02<br>Subscriber"]
        A --> D["WAS 03<br>Subscriber"]
        B --> E["duplicateLearningCheck() 실행"]
        C --> F["duplicateLearningCheck() 실행"]
        D --> G["duplicateLearningCheck() 실행"]
    ```

    **Step 4. 중복 판단 및 알림**

    각 WAS에서:

    1. Redis Hash에서 해당 사용자의 모든 eventId 조회
    2. 자기 eventId 외 다른 eventId 발견 시
    3. CLIENTS Map에서 해당 SseEmitter 찾기
    4. 찾으면 "conflict" 이벤트 전송

### 4.2 Step 1: 이벤트 생성 - 상세 코드

**코드 위치**: `LessonSseService.java:51-78`

```java
public SseEmitter createEvent(String eventId) throws Exception {

    // 1. SSE Emitter 생성 (30분 타임아웃)
    SseEmitter emitter = new SerializableSseEmitter(SSE_SESSION_TIMEOUT);
    // SSE_SESSION_TIMEOUT = 30 * 60 * 1000L (30분)

    // 2. eventId에서 userNo 추출
    String[] dataArr = eventId.split(":");
    String userNo = dataArr[0];  // 예: "USER123"

    // 3. Redis Pub/Sub 채널 구독
    //    → 이 채널로 오는 메시지를 수신할 준비
    ChannelTopic channel = new ChannelTopic(
        lessonRedis.parseKey(userNo, MODULE_NAME)
    );
    // channel = "KNU10-LMS:lesson:USER123"
    redisMessageListener.addMessageListener(lessonRedisSubscriber, channel);

    // 4. WAS 메모리에 SseEmitter 저장
    //    → 현재 WAS에서만 접근 가능
    CLIENTS.put(eventId, emitter);
    // CLIENTS = ConcurrentHashMap<String, SseEmitter>

    // 5. Redis Hash에 eventId 저장
    //    → 모든 WAS에서 접근 가능 (중복 판단 기준)
    Map<String, Object> insertMap = new HashMap<>();
    insertMap.put(eventId, emitter);  // Hash Field = eventId
    lessonRedis.putHash(userNo, insertMap, CLIENT_SESSION_TIMEOUT, MODULE_NAME);
    // CLIENT_SESSION_TIMEOUT = 60 * 60 * 24 (86400초 = 24시간)
    // 결과: Redis Hash "KNU10-LMS:lesson:USER123"에 eventId 추가

    // 6. 클라이언트에 "created" 이벤트 전송
    sendToClient(emitter, eventId, "created", CLIENT_SESSION_TIMEOUT);

    // 7. 타임아웃/완료 시 자동 정리
    emitter.onTimeout(() -> this.deleteEvent(eventId));
    emitter.onCompletion(() -> this.deleteEvent(eventId));

    return emitter;
}
```

**이 시점의 Redis 상태:**

!!! note "Redis 상태 (createEvent 후)"

    - **KEY**: `KNU10-LMS:lesson:USER123`
    - **TYPE**: Hash
    - **TTL**: 86400초 (24시간)

    ```
    FIELDS:
    {
      "USER123:20251217:abc123:LESSON001": [SseEmitter객체]
    }
    ```

    ※ 첫 번째 세션 등록 완료

### 4.3 Step 2: 중복 체크 요청

**호출 URL**: `GET /lesson/sse/{eventId}/handler/DUPLICATE_LEARNING_CHECK?param=`

**코드 위치**: `LessonSseController.java:93-113`

```java
@GetMapping(value = "/lesson/sse/{eventId}/handler/{eventType}")
public void eventHandler(HttpServletRequest request,
        @PathVariable("eventId") String eventId,
        @PathVariable("eventType") String eventType,
        @RequestParam("param") String param) throws Exception {

    // 사용자 검증
    String userNo = UserBroker.getUserNo(request);
    String[] dataArr = eventId.split(":");
    if(ValidationUtils.isEmpty(userNo) || !userNo.equals(dataArr[0])) {
        return;
    }

    // 이벤트 타입별 처리
    switch (eventType) {
    case "STUDY_CHK":
        lessonSseService.publishMessage(eventId, eventType, param);
        break;
    case "DUPLICATE_LEARNING_CHECK":
        // ★ 중복 학습 체크 메시지 발행
        lessonSseService.publishMessage(eventId, eventType, "");
        break;
    }
}
```

**publishMessage 동작**: `LessonSseService.java:80-91`

```java
public void publishMessage(String eventId, String eventType, String param) {
    String[] dataArr = eventId.split(":");

    // Redis Pub/Sub 채널 생성
    ChannelTopic channel = new ChannelTopic(
        lessonRedis.parseKey(dataArr[0], MODULE_NAME)
    );
    // channel = "KNU10-LMS:lesson:USER123"

    // 메시지 객체 생성
    LessonPubSupVO lessonPubSupVO = new LessonPubSupVO();
    lessonPubSupVO.setEventId(eventId);
    lessonPubSupVO.setEventType("DUPLICATE_LEARNING_CHECK");
    lessonPubSupVO.setEventMsg("");

    // ★ 모든 WAS의 Subscriber에게 메시지 발행
    lessonRedisPublisher.publish(channel, lessonPubSupVO);
}
```

### 4.4 Step 3: 메시지 수신 (모든 WAS)

**코드 위치**: `LessonRedisSubscriber.java:23-40`

```java
@Service
public class LessonRedisSubscriber implements MessageListener {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private LessonSseService lessonSseService;

    /**
     * Redis로부터 메시지를 전달받음
     * → 모든 WAS에서 동시에 이 메서드가 호출됨
     */
    @Override
    public void onMessage(Message message, byte[] pattern) {
        if(redisTemplate.getValueSerializer().deserialize(message.getBody()) != null) {

            // 메시지 역직렬화
            LessonPubSupVO pubSupVO = (LessonPubSupVO)
                redisTemplate.getValueSerializer().deserialize(message.getBody());

            // 이벤트 타입별 분기
            switch (pubSupVO.getEventType()) {
            case "DUPLICATE_LEARNING_CHECK":
                // ★ 중복 학습 체크 로직 실행
                lessonSseService.duplicateLearningCheck(pubSupVO);
                break;
            case "STUDY_CHK":
                lessonSseService.studyCheck(pubSupVO);
                break;
            }
        }
    }
}
```

### 4.5 Step 4: 중복 판단 로직 (핵심!)

**코드 위치**: `LessonSseService.java:98-119`

```java
/**
 * 중복체크, 리스너 부분에서 호출.
 * <이중화 처리> 자신이 가지고 있는 EventId에만 conflict 이벤트를 전송함.
 */
public void duplicateLearningCheck(LessonPubSupVO pubSupVO) {

    String eventId = pubSupVO.getEventId();
    // 예: "USER123:20251217:abc123:LESSON001"

    String[] dataArr = eventId.split(":");
    String userNo = dataArr[0];  // "USER123"

    // ★ Redis Hash의 TTL 확인 (키 존재 여부)
    if (lessonRedis.getExpire(userNo, MODULE_NAME) > 0) {

        // ★ 해당 사용자의 모든 활성 세션(eventId) 조회
        Set<String> hashkeys = lessonRedis.getHashKeys(userNo, MODULE_NAME);
        // hashkeys = { "USER123:...:abc123:...", "USER123:...:def456:..." }

        Iterator<String> entries = hashkeys.iterator();

        while (entries.hasNext()) {
            String storeEventId = entries.next();

            if (eventId.equals(storeEventId)) {
                // ★ 자기 자신 → TTL만 갱신하고 스킵
                lessonRedis.refreshExpire(userNo, CLIENT_SESSION_TIMEOUT, MODULE_NAME);
                continue;

            } else {
                // ★ 다른 세션 발견! → 중복!
                if (CLIENTS.get(storeEventId) != null) {
                    // ★ 이 WAS에 해당 세션의 SseEmitter가 있으면
                    //    "conflict" 이벤트 전송
                    sendToClient(
                        CLIENTS.get(storeEventId),
                        storeEventId,
                        "conflict",
                        CLIENT_SESSION_TIMEOUT
                    );
                }
                // CLIENTS.get(storeEventId) == null이면
                // → 다른 WAS에 있는 세션이므로 여기서는 처리 안 함
                // → 해당 WAS의 Subscriber가 처리함
            }
        }
    }
}
```

**중복 판단 로직 시각화:**

!!! example "duplicateLearningCheck() 동작 원리"

    **입력**: `eventId = "USER123:20251217:def456:LESSON001"` (모바일에서 새로 접속한 세션)

    ---

    **1단계 - Redis Hash 조회**

    ```
    lessonRedis.getHashKeys("USER123", "lesson")
    → 결과: { "USER123:...:abc123:...",   ← PC 세션
             "USER123:...:def456:..." }  ← 모바일 세션 (나)
    ```

    ---

    **2단계 - 각 eventId 순회**

    `for storeEventId in hashkeys:`

    - **"abc123" (PC 세션)**
        - `eventId("def456") != storeEventId("abc123")`
        - 다른 세션! 중복 감지!
        - `CLIENTS.get("abc123")` 확인
        - 있으면 **"conflict" 전송**
    - **"def456" (모바일 세션 = 나)**
        - `eventId("def456") == storeEventId("def456")`
        - 자기 자신 → TTL 갱신만

    ---

    **결과**

    - PC 세션(abc123)에 "conflict" 이벤트 전송
    - PC 브라우저에서 "다른 기기에서 접속됨" 알림

---

## 5. 중복 시험 체크 - 완전 분석

### 5.1 학습 체크와의 차이점

**코드 위치**: `ExamSseService.java:98-123`

```java
public void duplicateCheck(ExamPubSupVO pubSupVO) {

    String eventId = pubSupVO.getEventId();
    // 예: "USER123:20251217:abc123:EXAM"

    String[] dataArr = eventId.split(":");
    String contentsType = dataArr[3];  // ★ "EXAM" 또는 다른 유형

    if (examRedis.getExpire(dataArr[0], MODULE_NAME) > 0) {
        Set<String> hashkeys = examRedis.getHashKeys(dataArr[0], MODULE_NAME);
        Iterator<String> entries = hashkeys.iterator();

        while (entries.hasNext()) {
            String storeEventId = entries.next();

            if (eventId.equals(storeEventId)) {
                examRedis.refreshExpire(dataArr[0], CLIENT_SESSION_TIMEOUT, MODULE_NAME);
                continue;
            } else {
                if (CLIENTS.get(storeEventId) != null) {
                    String[] dataArr2 = storeEventId.split(":");

                    // ★★★ 핵심 차이점 ★★★
                    // EXAM 타입끼리만 충돌 감지
                    if (contentsType.equals("EXAM") || dataArr2[3].equals("EXAM")) {
                        sendToClient(
                            CLIENTS.get(storeEventId),
                            storeEventId,
                            "response",  // "conflict" 대신 "response"
                            CLIENT_SESSION_TIMEOUT
                        );
                    }
                }
            }
        }
    }
}
```

### 5.2 학습 vs 시험 중복 체크 비교

!!! tip "학습 vs 시험 중복 체크 비교"

    | 항목 | 학습 (Lesson) | 시험 (Exam) |
    |------|-------------|-----------|
    | **체크 조건** | 모든 세션 대상 | EXAM 타입만 대상 |
    | **이벤트명** | "conflict" | "response" |
    | **dataArr[3] 사용 여부** | 콘텐츠ID (미사용) | 콘텐츠타입 (사용, 타입 필터링) |
    | **추가 기능** | 없음 | STOP (강제 종료) |

    **이유:**

    - **학습**: 모든 동시 접속 차단 (같은 강의)
    - **시험**: EXAM 타입만 차단 (다른 콘텐츠는 허용)

### 5.3 시험 강제 종료 (STOP)

**코드 위치**: `ExamSseService.java:125-146`

```java
public void stopRequest(ExamPubSupVO pubSupVO) {

    String eventId = pubSupVO.getEventId();
    String[] dataArr = eventId.split(":");

    if (examRedis.getExpire(dataArr[0], MODULE_NAME) > 0) {
        Set<String> hashkeys = examRedis.getHashKeys(dataArr[0], MODULE_NAME);
        Iterator<String> entries = hashkeys.iterator();

        while (entries.hasNext()) {
            String storeEventId = entries.next();

            if (eventId.equals(storeEventId)) {
                examRedis.refreshExpire(dataArr[0], CLIENT_SESSION_TIMEOUT, MODULE_NAME);
                continue;
            } else {
                if (CLIENTS.get(storeEventId) != null) {
                    // ★ 모든 다른 세션에 "stop" 이벤트 전송
                    sendToClient(
                        CLIENTS.get(storeEventId),
                        storeEventId,
                        "stop",
                        CLIENT_SESSION_TIMEOUT
                    );
                }
            }
        }
    }
}
```

---

## 6. 다중 WAS 환경 동작 원리

### 6.1 전체 아키텍처

!!! abstract "다중 WAS 환경 구조"

    ```mermaid
    graph TD
        subgraph Redis["Redis Server (133.186.251.121)"]
            HASH["Hash 저장소<br>KNU10-LMS:lesson:USER123<br>= { abc: emitter1, def: emitter2 }"]
            PUBSUB["Pub/Sub 채널<br>KNU10-LMS:lesson:USER123<br>(모든 WAS가 구독)"]
        end

        subgraph WAS1["WAS 01"]
            C1["CLIENTS Map<br>{ abc: emt1 }<br>Subscriber (구독 중)"]
        end

        subgraph WAS2["WAS 02"]
            C2["CLIENTS Map<br>{ def: emt2 }<br>Subscriber (구독 중)"]
        end

        subgraph WAS3["WAS 03"]
            C3["CLIENTS Map<br>{ (empty) }<br>Subscriber (구독 중)"]
        end

        Redis --> WAS1
        Redis --> WAS2
        Redis --> WAS3

        C1 -->|"SSE 연결"| PC["사용자A PC"]
        C2 -->|"SSE 연결"| MOBILE["사용자A 모바일"]
    ```

### 6.2 다중 WAS에서 중복 감지 시나리오

!!! example "다중 WAS 중복 감지 시나리오 (Step by Step)"

    **초기 상태**

    - 사용자A가 PC에서 WAS01에 연결됨 (eventId: abc)
    - Redis Hash: `{ "abc": ... }`
    - WAS01 CLIENTS: `{ "abc": emitter }`

    ---

    **Step 1. 모바일에서 WAS02에 새로 접속**

    `모바일 → WAS02: GET /lesson/sse/USER123:...:def:...`

    WAS02 동작:

    1. SseEmitter 생성
    2. `CLIENTS.put("def", emitter)` -- WAS02 메모리
    3. Redis Hash에 "def" 추가

    Redis Hash 상태: `{ "abc": ..., "def": ... }` -- 2개

    ---

    **Step 2. 모바일에서 중복 체크 요청**

    `모바일 → WAS02: GET /lesson/sse/.../handler/DUPLICATE_LEARNING_CHECK`

    WAS02 동작:

    1. `publishMessage()` 호출
    2. Redis Pub/Sub으로 메시지 발행

    ---

    **Step 3. 모든 WAS가 메시지 수신**

    Redis Pub/Sub → WAS01, WAS02, WAS03 동시 수신

    각 WAS에서 `duplicateLearningCheck()` 실행:

    !!! success "WAS01 처리"
        - Redis Hash 조회: `{ "abc", "def" }`
        - **"abc" 검사**:
            - "def" != "abc" → 다른 세션!
            - `CLIENTS.get("abc")` → emitter 존재!
            - **"abc" 세션에 "conflict" 전송**
        - **"def" 검사**:
            - "def" == "def" → 자기 자신, 스킵

    !!! note "WAS02 처리"
        - Redis Hash 조회: `{ "abc", "def" }`
        - **"abc" 검사**:
            - "def" != "abc" → 다른 세션!
            - `CLIENTS.get("abc")` → null (WAS02에 없음)
            - 아무것도 안 함 (WAS01이 처리)
        - **"def" 검사**:
            - "def" == "def" → 자기 자신, 스킵

    ---

    **결과**

    - WAS01이 PC 브라우저에 "conflict" 이벤트 전송
    - PC 브라우저에서 "다른 기기에서 접속됨" 알림 표시
    - PC 학습 종료 처리

### 6.3 핵심 포인트

!!! abstract "핵심 포인트 정리"

    1. **Redis Hash**는 "어떤 세션이 활성 상태인지" 공유 → 모든 WAS가 같은 정보 참조
    2. **Pub/Sub**은 "이벤트 발생"을 모든 WAS에 알림 → 모든 WAS에서 동시에 체크 로직 실행
    3. **CLIENTS Map**은 "실제 연결"을 해당 WAS만 보유 → `CLIENTS.get() != null`인 WAS만 실제 알림 전송
    4. 결과적으로 **"정확히 해당 세션을 가진 WAS"만 처리** → 중복 처리 없음, 누락 없음

---

## 7. 실제 시나리오별 동작

### 7.1 시나리오 1: PC에서 학습 중, 모바일로 같은 강의 접속

!!! example "PC 학습 중 → 모바일 동일 강의 접속"

    **Before**

    - PC: LESSON001 학습 중 (eventId: abc)
    - Redis: `{ "abc" }`

    **Action**

    - 모바일: LESSON001 접속 (eventId: def)
    - 모바일: DUPLICATE_LEARNING_CHECK 요청

    **After**

    - PC: "conflict" 이벤트 수신 → 학습 중단 알림
    - 모바일: 정상 학습 진행
    - Redis: `{ "abc", "def" }` → "abc" 제거 → `{ "def" }`

### 7.2 시나리오 2: 시험 중 다른 탭에서 같은 시험 접속

!!! example "시험 중 → 새 탭에서 같은 시험 접속"

    **Before**

    - Tab1: EXAM 응시 중 (eventId: xxx:EXAM)
    - Redis: `{ "xxx:EXAM" }`

    **Action**

    - Tab2: 같은 EXAM 접속 (eventId: yyy:EXAM)
    - Tab2: DUPLICATE_CHECK 요청

    **After**

    - Tab1: "response" 이벤트 수신 → 시험 중단 경고
    - Tab2: 정상 시험 진행 또는 차단

    ※ EXAM 타입끼리만 충돌 감지

### 7.3 시나리오 3: 교수가 시험 강제 종료

!!! example "교수가 시험 강제 종료 버튼 클릭"

    **Before**

    - 학생A, B, C: 시험 응시 중
    - 각각 WAS01, WAS02, WAS03에 연결

    **Action**

    - 교수: STOP 이벤트 발행

    **Process**

    1. Redis Pub/Sub으로 STOP 메시지 발행
    2. 모든 WAS가 메시지 수신
    3. 각 WAS에서 `stopRequest()` 실행
    4. 각 WAS의 CLIENTS에 있는 세션에 "stop" 전송

    **After**

    - 학생A (WAS01): "stop" 수신 → 답안 자동 제출
    - 학생B (WAS02): "stop" 수신 → 답안 자동 제출
    - 학생C (WAS03): "stop" 수신 → 답안 자동 제출

---

## 8. 관련 파일 목록

### 8.1 Core 파일

| 파일 | 위치 | 역할 |
|------|------|------|
| **LessonSseService.java** | `lms/core/lesson/service/` | 학습 SSE 이벤트 관리 |
| **ExamSseService.java** | `lms/core/exam/service/` | 시험 SSE 이벤트 관리 |
| **LessonSseController.java** | `lms/web/lesson/` | 학습 SSE API 엔드포인트 |
| **ExamSseController.java** | `lms/web/exam/` | 시험 SSE API 엔드포인트 |

### 8.2 Redis Component 파일

| 파일 | 위치 | 역할 |
|------|------|------|
| **RedisComponent.java** | `common/comm/util/redis/` | 공통 Redis 연산 |
| **LessonRedisComponent.java** | `lms/core/lesson/redis/` | 학습 전용 Redis (MODULE="lesson") |
| **ExamRedisComponent.java** | `lms/core/exam/service/redis/` | 시험 전용 Redis (MODULE="exam") |

### 8.3 Pub/Sub 파일

| 파일 | 위치 | 역할 |
|------|------|------|
| **LessonRedisPublisher.java** | `lms/core/lesson/redis/pubsub/` | 학습 이벤트 발행 |
| **LessonRedisSubscriber.java** | `lms/core/lesson/redis/pubsub/` | 학습 이벤트 구독 |
| **ExamRedisPublisher.java** | `lms/core/exam/service/redis/pubsub/` | 시험 이벤트 발행 |
| **ExamRedisSubscriber.java** | `lms/core/exam/service/redis/pubsub/` | 시험 이벤트 구독 |

### 8.4 VO 파일

| 파일 | 위치 | 역할 |
|------|------|------|
| **LessonPubSupVO.java** | `lms/core/lesson/redis/pubsub/` | 학습 Pub/Sub 메시지 VO |
| **ExamPubSupVO.java** | `lms/core/exam/service/redis/pubsub/` | 시험 Pub/Sub 메시지 VO |

---

## 요약

| 항목 | 내용 |
|------|------|
| **Redis 키** | `{SITE}:{MODULE}:{USER_NO}` (Hash 타입) |
| **EventId** | `{USER_NO}:{날짜}:{랜덤값}:{콘텐츠ID/타입}` |
| **중복 판단** | Redis Hash에 같은 USER_NO의 다른 eventId 존재 여부 |
| **알림 방식** | Pub/Sub → 모든 WAS 수신 → CLIENTS에서 찾으면 SSE 전송 |
| **학습 이벤트** | `conflict` (모든 세션 대상) |
| **시험 이벤트** | `response` (EXAM 타입만), `stop` (강제 종료) |

---

**참고 문서**:
- [04_실제_코드_패턴_분석.md](./04_실제_코드_패턴_분석.md)
- [02_프로젝트별_Redis_적용현황.md](./02_프로젝트별_Redis_적용현황.md)
