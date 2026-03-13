# 프로젝트별 Redis 적용 현황 분석

**작성일**: 2025-12-17
**대상 프로젝트**: KNU10WebService (HUB), LXP-KNU10 (LMS), LXP-SYNC (연동)
**난이도**: ★★☆☆☆ ~ ★★★☆☆

---

## 목차
1. [프로젝트 개요](#1-프로젝트-개요)
2. [KNU10WebService (HUB) - Redis 적용 현황](#2-knu10webservice-hub---redis-적용-현황)
3. [LXP-KNU10 (LMS) - Redis 적용 현황](#3-lxp-knu10-lms---redis-적용-현황)
4. [LXP-SYNC (연동) - Redis 적용 현황](#4-lxp-sync-연동---redis-적용-현황)
5. [프로젝트 간 Redis 비교](#5-프로젝트-간-redis-비교)

---

## 1. 프로젝트 개요

!!! note "시스템 구성도"
    ```mermaid
    graph TD
        USER["사용자 (학생/교수)"] --> HUB

        subgraph HUB["KNU10WebService (HUB)"]
            H1["통합 포털 역할"]
            H2["로그인/SSO 처리"]
            H3["중복 로그인 방지 (Redis)"]
        end

        HUB --> LMS["LXP-KNU10 (LMS)<br>학습관리 / 시험응시 / 강의수강"]
        HUB --> SYNC["LXP-SYNC (연동)<br>데이터 동기화 / HUB-학사 연동"]
        HUB --> ETC["기타 시스템<br>(학사, CMS 등)"]

        LMS --> REDIS["Redis Server<br>133.186.251.121<br>Port: 6379"]
        SYNC --> REDIS
        HUB --> REDIS
    ```

---

## 2. KNU10WebService (HUB) - Redis 적용 현황

### 2.1 프로젝트 정보

| 항목 | 내용 |
|------|------|
| **프로젝트명** | KNU10WebService |
| **역할** | 통합 포털 (HUB) |
| **프레임워크** | Spring Boot |
| **Redis 클라이언트** | Lettuce |
| **주요 기능** | 중복 로그인 방지 |

### 2.2 Redis 관련 파일 구조

```
KNU10WebService/
└── src/main/java/kr/co/mediopia/coss/hub/
    ├── config/
    │   └── RedisConfig.java           ← Redis 설정
    ├── common/
    │   ├── utils/
    │   │   ├── RedisUtil.java         ← Redis 유틸리티
    │   │   └── SessionUtil.java       ← 세션 관리 (Redis 사용)
    │   └── interceptor/
    │       └── LoginDupCheckInterceptor.java  ← 중복 로그인 체크
    └── resources/
        ├── application.properties      ← Redis 설정 (로컬/개발)
        └── application-dev.properties  ← Redis 설정 (운영)
```

### 2.3 Redis 설정 상세 (application.properties)

```properties
# Redis 연결 풀 설정
spring.redis.lettuce.pool.max-active=5   # 최대 활성 연결 수
spring.redis.lettuce.pool.max-idle=5     # 최대 유휴 연결 수
spring.redis.lettuce.pool.min-idle=3     # 최소 유휴 연결 수

# Redis 서버 정보
spring.redis.host=133.186.251.121        # Redis 서버 IP
spring.redis.port=6379                   # Redis 포트 (기본값)
spring.redis.password=medi-redis8500     # 인증 비밀번호

# 키 접두어 (환경 구분)
spring.redis.key-prefix=KNU10-HUB-TEST:  # 개발 환경
# spring.redis.key-prefix=KNU10-HUB:     # 운영 환경
```

### 2.4 RedisConfig.java 상세 분석

```java
// 파일: RedisConfig.java
// 위치: src/main/java/kr/co/mediopia/coss/hub/config/

public class RedisConfig {

    // application.properties에서 값을 주입받음
    @Value("${spring.redis.host}")
    private String host;          // Redis 서버 주소

    @Value("${spring.redis.port}")
    private int port;             // Redis 포트

    @Value("${spring.redis.password}")
    private String password;      // Redis 비밀번호

    /**
     * Redis 연결 팩토리 생성
     * - Lettuce 클라이언트 사용 (Jedis 대비 성능 우수)
     * - Standalone 모드 (단일 Redis 서버)
     */
    @Bean
    RedisConnectionFactory redisConnectionFactory() {
        // Redis 서버 설정 객체 생성
        RedisStandaloneConfiguration redisConfiguration = new RedisStandaloneConfiguration();
        redisConfiguration.setHostName(host);      // 호스트 설정
        redisConfiguration.setPort(port);          // 포트 설정
        redisConfiguration.setPassword(password);  // 비밀번호 설정

        // Lettuce 연결 팩토리 생성
        LettuceConnectionFactory lettuceConnectionFactory =
            new LettuceConnectionFactory(redisConfiguration);
        return lettuceConnectionFactory;
    }

    /**
     * RedisTemplate 생성
     * - Redis 명령을 실행하기 위한 핵심 클래스
     * - Key, Value 모두 String 직렬화 사용
     */
    @Bean
    RedisTemplate<String, String> redisTemplate() {
        RedisTemplate<String, String> redisTemplate = new RedisTemplate<>();

        // Key를 String으로 직렬화 (예: "KNU10-HUB:user123")
        redisTemplate.setKeySerializer(new StringRedisSerializer());

        // Value도 String으로 직렬화 (예: "session_id_abc123")
        redisTemplate.setValueSerializer(new StringRedisSerializer());

        // 연결 팩토리 설정
        redisTemplate.setConnectionFactory(redisConnectionFactory());

        return redisTemplate;
    }
}
```

### 2.5 RedisUtil.java 상세 분석

```java
// 파일: RedisUtil.java
// 위치: src/main/java/kr/co/mediopia/coss/hub/common/utils/

@Component
public class RedisUtil {

    // RedisTemplate 주입 (static으로 사용하기 위한 특별한 패턴)
    private static RedisTemplate<String, String> redisTemplate;

    // 키 접두어 (환경 구분용)
    public static String REDIS_KEY_PREFIX;  // 예: "KNU10-HUB-TEST:"

    @Value("${spring.redis.key-prefix}")
    public void setREDIS_KEY_PREFIX(String prefix) {
        REDIS_KEY_PREFIX = prefix;
    }

    @Autowired
    public RedisUtil(RedisTemplate<String, String> redisTemplate) {
        RedisUtil.redisTemplate = redisTemplate;
    }

    /**
     * Key-Value 저장 (24시간 유효)
     *
     * 사용 예시:
     *   RedisUtil.addKeyValue("user123", "session_abc")
     *   → Redis에 저장: "KNU10-HUB-TEST:user123" = "session_abc"
     */
    public static void addKeyValue(String key, String value) {
        ValueOperations<String, String> vop = redisTemplate.opsForValue();
        vop.set(REDIS_KEY_PREFIX + key, value);

        // 24시간 후 자동 삭제 (TTL 설정)
        redisTemplate.expire(REDIS_KEY_PREFIX + key, 24, TimeUnit.HOURS);
    }

    /**
     * Key로 Value 조회
     *
     * 동작 방식:
     * 1. Redis에서 값 조회
     * 2. 값이 있으면 TTL 갱신 (슬라이딩 세션)
     * 3. 값이 없으면 "empty" 반환
     */
    public static String getValueByKey(String key) {
        ValueOperations<String, String> vop = redisTemplate.opsForValue();
        String retVal = StringUtil.nvl(vop.get(REDIS_KEY_PREFIX + key), "empty");

        // 조회 성공 시 TTL 갱신 (24시간 연장)
        if(!retVal.equals("empty")) {
            redisTemplate.expire(REDIS_KEY_PREFIX + key, 24, TimeUnit.HOURS);
        }
        return retVal;
    }

    /**
     * Key와 Value가 일치할 때만 삭제
     *
     * 사용 목적:
     * - 로그아웃 시 본인의 세션만 삭제
     * - 다른 사용자가 이미 새 세션을 만들었으면 삭제하지 않음
     */
    public static void removeByKeyAndValue(String key, String value) {
        ValueOperations<String, String> vop = redisTemplate.opsForValue();
        String redisVal = StringUtil.nvl(vop.get(REDIS_KEY_PREFIX + key), "empty");

        // 저장된 값과 일치할 때만 삭제
        if(redisVal.equals(value)) {
            redisTemplate.delete(REDIS_KEY_PREFIX + key);
        }
    }
}
```

### 2.6 중복 로그인 방지 로직

!!! example "HUB 중복 로그인 방지 흐름도"
    **[로그인 시]**

    1. 사용자가 로그인
    2. `SessionUtil.setLoginInfoSession()` 호출
        - `RedisUtil.addKeyValue(userId, sessionId)`
        - Redis: `SET "KNU10-HUB:user123" "sess_abc"` / `EXPIRE "KNU10-HUB:user123" 86400`

    **[페이지 접근 시]**

    3. `LoginDupCheckInterceptor.preHandle()` 실행
        - Redis에서 현재 유효 세션 조회: `redisSessionId = RedisUtil.getValueByKey(userId)`
        - 비교:
            - 현재 세션 == Redis 세션 → **정상 접근**
            - 현재 세션 ≠ Redis 세션 → **로그아웃 처리** (다른 곳에서 새로 로그인했음)

    **[로그아웃 시]**

    4. `SessionUtil.logout()` 호출
        - `RedisUtil.removeByKeyAndValue(userId, sessionId)` (본인 세션일 때만 Redis에서 삭제)

### 2.7 실제 코드 흐름

```java
// === 1. 로그인 시 (SessionUtil.java:23-29) ===
public static void setLoginInfoSession(HttpSession session, LoginInfo info) {
    if (SessionUtil.getLoginInfo(session) == null) {
        // 세션에 로그인 정보 저장
        session.setAttribute(Constants.SESSION_LOGIN_INFO, info);

        // ★ Redis에 사용자ID → 세션ID 매핑 저장
        RedisUtil.addKeyValue(info.getUserId(), session.getId());
    }
}

// === 2. 페이지 접근 시 (LoginDupCheckInterceptor.java:18-39) ===
@Override
public boolean preHandle(HttpServletRequest request,
                         HttpServletResponse response,
                         Object handler) throws Exception {

    // 로그인 안 된 사용자는 통과
    if (!SessionUtil.isLogin(request)) {
        return true;
    }

    HttpSession session = request.getSession();
    LoginInfo loginInfo = SessionUtil.getLoginInfo(session);

    // ★ Redis에서 현재 유효한 세션ID 조회
    String sessionId = RedisUtil.getValueByKey(loginInfo.getUserId());

    // 세션 불일치 = 다른 곳에서 로그인함
    if(sessionId.equals("empty") || !sessionId.equals(session.getId())) {
        SessionUtil.logout(session, request, response);
        response.sendRedirect("/");  // 메인 페이지로 이동
        return false;
    }

    return true;  // 정상 접근
}

// === 3. 로그아웃 시 (SessionUtil.java:86-110) ===
public static boolean logout(HttpSession session,
                            HttpServletRequest request,
                            HttpServletResponse response) {
    LoginInfo info = getLoginInfo(session);

    if(info != null) {
        // ★ Redis에서 세션 정보 삭제 (본인 세션일 때만)
        RedisUtil.removeByKeyAndValue(info.getUserId(), session.getId());
    }

    // 세션 무효화
    session.removeAttribute(Constants.SESSION_LOGIN_INFO);
    session.invalidate();

    // ... 쿠키 처리 ...
    return false;
}
```

---

## 3. LXP-KNU10 (LMS) - Redis 적용 현황

### 3.1 프로젝트 정보

| 항목 | 내용 |
|------|------|
| **프로젝트명** | LXP-KNU10 |
| **역할** | 학습관리시스템 (LMS) |
| **프레임워크** | eGovFramework (Spring 기반) |
| **Redis 클라이언트** | Lettuce |
| **주요 기능** | 학습 중복 방지, 시험 관리, 실시간 알림 |

### 3.2 Redis 관련 파일 구조

```
LXP-KNU10/
└── src/main/java/egovframework/mediopia/lxp/
    ├── common/
    │   ├── Constants.java                  ← Redis 상수 정의
    │   └── comm/util/redis/
    │       └── RedisComponent.java         ← 공통 Redis 컴포넌트
    ├── home/core/redis/pubsub/
    │   ├── UsrRedisPublisher.java          ← 사용자 이벤트 발행
    │   ├── UsrRedisSubscriber.java         ← 사용자 이벤트 구독
    │   └── UsrPubSupVO.java                ← 메시지 VO
    └── lms/core/
        ├── exam/service/redis/
        │   ├── ExamRedisComponent.java     ← 시험 전용 Redis
        │   └── pubsub/
        │       ├── ExamRedisPublisher.java
        │       ├── ExamRedisSubscriber.java
        │       └── ExamPubSupVO.java
        └── lesson/redis/
            ├── LessonRedisComponent.java   ← 학습 전용 Redis
            └── pubsub/
                ├── LessonRedisPublisher.java
                ├── LessonRedisSubscriber.java
                └── LessonPubSupVO.java
```

### 3.3 Redis 설정 (context-common.xml)

```xml
<!-- Redis 연결 설정 -->
<bean id="redisConnectionFactory"
      class="org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory"
      p:host-name="${lxp.redis.host}"   <!-- 서버 주소 -->
      p:port="${lxp.redis.port}"         <!-- 포트 -->
      p:database="1"/>                   <!-- DB 번호 (0~15) -->
<!--
    주의: password 프로퍼티는 주석 처리됨
    이유: 연결 풀링 시 재연결에서 password를 참조하지 않는 이슈
    권장: Redis는 WAS에서만 연결 허용하도록 네트워크 설정
-->

<!-- 문자열 직렬화기 -->
<bean id="stringRedisSerializer"
      class="org.springframework.data.redis.serializer.StringRedisSerializer"/>

<!-- Pub/Sub 리스너 컨테이너 -->
<bean id="redisMessageListener"
      class="org.springframework.data.redis.listener.RedisMessageListenerContainer"
      p:connectionFactory-ref="redisConnectionFactory"/>

<!-- RedisTemplate (핵심) -->
<bean id="redisTemplate"
      class="org.springframework.data.redis.core.RedisTemplate"
      p:connectionFactory-ref="redisConnectionFactory"
      p:keySerializer-ref="stringRedisSerializer"
      p:hashKeySerializer-ref="stringRedisSerializer"/>
```

### 3.4 Constants.java - Redis 상수

```java
// Redis 관련 상수 (Constants.java 발췌)
public class Constants {
    // ...

    // Redis 사이트 식별자 (키 접두어)
    public static final String REDIS_SITE =
        framework.getString("framework.lxp.redis.site");
    // 예: "KNU10-LMS"

    // 기본 TTL (초 단위)
    public static final long REDIS_DEFULT_EXPIRE =
        framework.getLong("framework.lxp.redis.defult.expire");
    // 예: 3600 (1시간)

    // Redis 사용 여부
    public static final String REDIS_USEYN =
        framework.getString("framework.lxp.redis.useyn");
    // "Y" 또는 "N"
}
```

### 3.5 RedisComponent.java 상세 분석 (공통 컴포넌트)

```java
@Component
public class RedisComponent {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    // 다양한 데이터 타입 지원
    @Resource(name ="redisTemplate")
    private ValueOperations<String, String> stringValOps;   // 문자열

    @Resource(name ="redisTemplate")
    private ListOperations<String, Object> listValOps;      // 리스트

    @Resource(name ="redisTemplate")
    private HashOperations<String, String, Object> hashValOps;  // 해시

    private static String REDIS_SITE = Constants.REDIS_SITE;
    private static long REDIS_DEFULT_EXPIRE = Constants.REDIS_DEFULT_EXPIRE;

    /**
     * 키 생성 규칙
     * 형식: {사이트}:{모듈}:{키}
     * 예: "KNU10-LMS:lesson:user123_course456"
     */
    public String parseKey(String key, String moduleName) {
        return String.format("%s:%s:%s", REDIS_SITE, moduleName, key);
    }

    // === 문자열 (String) 연산 ===

    public void setString(String key, String value, long expire, String moduleName) {
        stringValOps.set(parseKey(key, moduleName), value, expire, TimeUnit.SECONDS);
    }

    public String getString(String key, String moduleName) {
        try {
            return (String) stringValOps.get(parseKey(key, moduleName));
        } catch (Exception e) {
            return null;
        }
    }

    // === 해시 (Hash) 연산 ===

    public void putHash(String key, Map<String, Object> value,
                        long expire, String moduleName) {
        hashValOps.putAll(parseKey(key, moduleName), value);
        redisTemplate.expire(parseKey(key, moduleName), expire, TimeUnit.SECONDS);
    }

    public Object getHash(String key, String hashKey, String moduleName) {
        try {
            return hashValOps.get(parseKey(key, moduleName), hashKey);
        } catch (Exception e) {
            return null;
        }
    }

    // === 리스트 (List) 연산 ===

    public void pushList(String key, Object value, long expire, String moduleName) {
        listValOps.leftPush(parseKey(key, moduleName), value);
        redisTemplate.expire(parseKey(key, moduleName), expire, TimeUnit.SECONDS);
    }

    public List<Object> getList(String key, String moduleName) {
        try {
            return listValOps.range(parseKey(key, moduleName), 0, -1);
        } catch (Exception e) {
            return null;
        }
    }

    // === 공통 연산 ===

    public boolean isKey(String key, String moduleName) {
        return redisTemplate.hasKey(parseKey(key, moduleName));
    }

    public void delete(String key, String moduleName) {
        redisTemplate.delete(parseKey(key, moduleName));
    }

    public void refreshExpire(String key, long expire, String moduleName) {
        redisTemplate.expire(parseKey(key, moduleName), expire, TimeUnit.SECONDS);
    }
}
```

### 3.6 모듈별 Redis 컴포넌트 (Exam, Lesson)

```java
// ExamRedisComponent.java - 시험 전용
@Component
public class ExamRedisComponent {
    private static String MODULE_NAME = "exam";  // 모듈명 고정

    // parseKey 결과: "KNU10-LMS:exam:{key}"
    public String parseKey(String key) {
        return String.format("%s:%s:%s", REDIS_SITE, MODULE_NAME, key);
    }

    // 나머지는 RedisComponent와 동일한 패턴
}

// LessonRedisComponent.java - 학습 전용
@Component
public class LessonRedisComponent {
    private static String MODULE_NAME = "lesson";  // 모듈명 고정

    // parseKey 결과: "KNU10-LMS:lesson:{key}"
    public String parseKey(String key) {
        return String.format("%s:%s:%s", REDIS_SITE, MODULE_NAME, key);
    }
}
```

### 3.7 Pub/Sub (발행/구독) 구현

!!! note "LMS Pub/Sub 아키텍처"
    ```mermaid
    graph TD
        subgraph REDIS["Redis Server"]
            CH1["Channel: exam_event"]
            CH2["Channel: lesson_event"]
            CH3["Channel: user_event"]
        end

        WAS1["WAS 1<br>(Publisher / 이벤트 발행)"] --> REDIS
        REDIS --> WAS2["WAS 2<br>(Subscriber / 이벤트 수신)"]
        REDIS --> WAS1
    ```

    **사용 예시:**

    - 교수가 시험 종료 → 모든 WAS에 전파 → 학생들 강제 제출
    - 중복 로그인 감지 → 모든 WAS에 전파 → 기존 세션 종료
    - 학습 중복 감지 → 해당 WAS에 알림 → 기존 학습 종료

### 3.8 Pub/Sub 코드 상세

```java
// === Publisher (발행자) ===
@Service
public class ExamRedisPublisher {
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    /**
     * 시험 이벤트 발행
     * @param topic 채널 (예: ChannelTopic("exam_event"))
     * @param examPubSupVO 전송할 메시지 객체
     */
    public void publish(ChannelTopic topic, ExamPubSupVO examPubSupVO) {
        redisTemplate.convertAndSend(topic.getTopic(), examPubSupVO);
    }
}

// === Subscriber (구독자) ===
@Service
public class ExamRedisSubscriber implements MessageListener {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    @Autowired
    private ExamSseService examSseService;  // SSE 서비스 (실시간 알림)

    /**
     * Redis 메시지 수신 시 자동 호출
     */
    @Override
    public void onMessage(Message message, byte[] pattern) {
        if(redisTemplate.getValueSerializer().deserialize(message.getBody()) != null) {

            // 메시지 역직렬화
            ExamPubSupVO pubSupVO = (ExamPubSupVO)
                redisTemplate.getValueSerializer().deserialize(message.getBody());

            // 이벤트 타입별 분기 처리
            switch (pubSupVO.getEventType()) {

                case "DUPLICATE_CHECK":
                    // 시험 중복 응시 체크
                    examSseService.duplicateCheck(pubSupVO);
                    break;

                case "STOP":
                    // 시험 강제 종료 요청
                    examSseService.stopRequest(pubSupVO);
                    break;
            }
        }
    }
}
```

### 3.9 이벤트 타입별 사용처

!!! info "LMS Redis 이벤트 목록"
    **User 이벤트 (UsrRedisSubscriber)**

    - `DUPLICATE_LOGIN_CHECK` - 중복 로그인 감지 시 기존 세션 종료

    **Exam 이벤트 (ExamRedisSubscriber)**

    - `DUPLICATE_CHECK` - 시험 중복 응시 감지
    - `STOP` - 교수가 시험 강제 종료

    **Lesson 이벤트 (LessonRedisSubscriber)**

    - `DUPLICATE_LEARNING_CHECK` - 동시 학습 감지 (같은 강좌 여러 기기)
    - `STUDY_CHK` - 학습 상태 확인

---

## 4. LXP-SYNC (연동) - Redis 적용 현황

### 4.1 분석 결과

!!! warning "LXP-SYNC Redis 현황"
    **Redis 직접 사용 없음**

    **이유:**

    - LXP-SYNC는 HUB와 학사시스템 간 데이터 동기화 담당
    - 배치성 작업 위주 (실시간 세션 관리 불필요)
    - Redis 관련 설정 파일 미발견

    ```mermaid
    graph LR
        HUB["HUB"] -->|API| SYNC["LXP-SYNC"] -->|SQL| DB["학사DB"]
    ```

    LXP-SYNC는 REST API와 DB 연동만 수행

---

## 5. 프로젝트 간 Redis 비교

### 5.1 비교표

| 항목 | KNU10WebService (HUB) | LXP-KNU10 (LMS) | LXP-SYNC |
|------|----------------------|-----------------|----------|
| **Redis 사용** | ✅ 사용 | ✅ 사용 | ❌ 미사용 |
| **프레임워크** | Spring Boot | eGovFramework | - |
| **설정 방식** | Java Config | XML Config | - |
| **클라이언트** | Lettuce | Lettuce | - |
| **데이터 타입** | String | String, Hash, List | - |
| **Pub/Sub** | ❌ 미사용 | ✅ 사용 | - |
| **키 접두어** | `KNU10-HUB:` | `KNU10-LMS:모듈:` | - |
| **DB 번호** | 0 (기본) | 1 | - |

### 5.2 키 네이밍 패턴

!!! info "Redis 키 네이밍 규칙"
    **HUB:**

    - `KNU10-HUB:{userId}` (예: `KNU10-HUB:user123`)
    - 값: 세션ID

    **LMS:** (`{사이트}:{모듈}:{키}` 패턴)

    - `KNU10-LMS:lesson:{key}` (예: `KNU10-LMS:lesson:user123_course456`)
    - `KNU10-LMS:exam:{key}` (예: `KNU10-LMS:exam:user123_exam789`)
    - `KNU10-LMS:user:{key}` (예: `KNU10-LMS:user:session_info`)

### 5.3 아키텍처 다이어그램

!!! abstract "전체 Redis 아키텍처"
    ```mermaid
    graph TD
        subgraph REDIS["Redis Server (133.186.251.121)"]
            DB0["DB 0: HUB"]
            DB1["DB 1: LMS"]
        end

        HUB["HUB (WAS)<br>로그인 처리 / SSO / 중복로그인"] --> DB0

        LMS1["LMS (WAS 1)<br>학습 관리 / 시험 관리 / Pub/Sub"] --> DB1
        LMS2["LMS WAS 2<br>Pub/Sub 구독자"] --> DB1
        LMS3["LMS WAS 3<br>Pub/Sub 구독자"] --> DB1
    ```

---

**다음 문서**: [03_Redis_설정_상세분석.md](./03_Redis_설정_상세분석.md)
