# Redis 설정 상세 분석

**작성일**: 2025-12-17
**대상**: 신입 개발자
**난이도**: ★★★☆☆

---

## 목차
1. [Spring Boot 설정 (HUB)](#1-spring-boot-설정-hub)
2. [XML 설정 (LMS)](#2-xml-설정-lms)
3. [Redis 연결 풀 설정](#3-redis-연결-풀-설정)
4. [직렬화(Serialization) 설정](#4-직렬화serialization-설정)
5. [TTL (Time To Live) 설정](#5-ttl-time-to-live-설정)
6. [Pub/Sub 설정](#6-pubsub-설정)
7. [환경별 설정 분리](#7-환경별-설정-분리)

---

## 1. Spring Boot 설정 (HUB)

### 1.1 설정 파일 위치

```
KNU10WebService/
└── src/main/
    ├── java/.../config/
    │   └── RedisConfig.java         ← Java 기반 설정
    └── resources/
        ├── application.properties    ← 공통/개발 설정
        └── application-dev.properties ← 운영 설정
```

### 1.2 application.properties 상세 해설

```properties
# ========================================
# Redis 연결 풀 설정 (Lettuce)
# ========================================

# 동시에 활성화할 수 있는 최대 연결 수
# → Redis에 동시 요청이 많을 때 필요
spring.redis.lettuce.pool.max-active=5

# 연결 풀에 유지할 최대 유휴(idle) 연결 수
# → 사용 안 할 때도 이만큼은 연결 유지
spring.redis.lettuce.pool.max-idle=5

# 연결 풀에 유지할 최소 유휴 연결 수
# → 항상 이만큼은 연결 대기 상태 유지
spring.redis.lettuce.pool.min-idle=3

# ========================================
# Redis 서버 연결 정보
# ========================================

# Redis 서버 IP 주소
spring.redis.host=133.186.251.121

# Redis 포트 (기본값: 6379)
spring.redis.port=6379

# Redis 인증 비밀번호
spring.redis.password=medi-redis8500

# ========================================
# 애플리케이션 설정
# ========================================

# 키 접두어 (환경 구분용)
# 개발: KNU10-HUB-TEST:
# 운영: KNU10-HUB:
spring.redis.key-prefix=KNU10-HUB-TEST:
```

### 1.3 연결 풀 설정 시각화

!!! note "Redis 연결 풀 동작 방식"
    ```mermaid
    graph TD
        subgraph WAS["WAS (Spring Boot Application)"]
            subgraph POOL["Connection Pool (max-active=5)"]
                S1["슬롯 1<br>사용중"]
                S2["슬롯 2<br>사용중"]
                S3["슬롯 3<br>대기"]
                S4["슬롯 4<br>대기"]
                S5["슬롯 5<br>대기"]
            end
        end

        S1 --> REDIS["Redis Server<br>133.186.251.121"]
        S2 --> REDIS
    ```

    - **min-idle=3**: 최소 3개는 항상 대기
    - **max-idle=5**: 유휴 상태 최대 5개

    **동작 흐름:**

    1. 요청 → 풀에서 사용 가능한 연결 가져옴
    2. Redis 명령 실행
    3. 연결 반납 → 풀로 돌아감
    4. 연결 부족 시 → 새 연결 생성 (max-active까지)

### 1.4 RedisConfig.java 설정 상세

```java
/**
 * Redis 설정 클래스
 *
 * @Configuration 대신 그냥 클래스로 정의됨
 * → 실제로는 @Configuration 추가 필요할 수 있음
 */
public class RedisConfig {

    // === 프로퍼티 값 주입 ===

    @Value("${spring.redis.host}")
    private String host;
    // 설명: application.properties의 spring.redis.host 값을 주입
    // 예시값: "133.186.251.121"

    @Value("${spring.redis.port}")
    private int port;
    // 설명: Redis 포트
    // 예시값: 6379

    @Value("${spring.redis.password}")
    private String password;
    // 설명: Redis 인증 비밀번호
    // 예시값: "medi-redis8500"

    // === Bean 정의 ===

    /**
     * Redis 연결 팩토리 Bean
     *
     * RedisStandaloneConfiguration: 단일 Redis 서버 연결 설정
     * LettuceConnectionFactory: Lettuce 클라이언트 사용
     *
     * Lettuce vs Jedis 비교:
     * ┌─────────────┬─────────────────────────────────────────┐
     * │   Lettuce   │ 비동기, Netty 기반, 더 빠름              │
     * │   Jedis     │ 동기, 오래된 방식, 스레드 안전성 이슈    │
     * └─────────────┴─────────────────────────────────────────┘
     */
    @Bean
    RedisConnectionFactory redisConnectionFactory() {
        // 1. Redis 서버 설정 객체 생성
        RedisStandaloneConfiguration redisConfiguration =
            new RedisStandaloneConfiguration();

        // 2. 연결 정보 설정
        redisConfiguration.setHostName(host);      // 서버 주소
        redisConfiguration.setPort(port);          // 포트
        redisConfiguration.setPassword(password);  // 비밀번호

        // 3. Lettuce 연결 팩토리 생성 및 반환
        LettuceConnectionFactory lettuceConnectionFactory =
            new LettuceConnectionFactory(redisConfiguration);

        return lettuceConnectionFactory;
    }

    /**
     * RedisTemplate Bean
     *
     * Redis 명령을 실행하기 위한 핵심 클래스
     * Key-Value 모두 String 타입으로 직렬화
     *
     * 직렬화란?
     * → 객체를 바이트 스트림으로 변환하는 과정
     * → Redis는 바이너리 데이터만 저장 가능
     * → String으로 직렬화하면 Redis CLI에서도 읽기 쉬움
     */
    @Bean
    RedisTemplate<String, String> redisTemplate() {
        RedisTemplate<String, String> redisTemplate = new RedisTemplate<>();

        // Key 직렬화: String
        // 예: "KNU10-HUB:user123" → "KNU10-HUB:user123" (그대로)
        redisTemplate.setKeySerializer(new StringRedisSerializer());

        // Value 직렬화: String
        // 예: "session_abc123" → "session_abc123" (그대로)
        redisTemplate.setValueSerializer(new StringRedisSerializer());

        // 연결 팩토리 설정
        redisTemplate.setConnectionFactory(redisConnectionFactory());

        return redisTemplate;
    }
}
```

---

## 2. XML 설정 (LMS)

### 2.1 context-common.xml 상세 해설

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:context="http://www.springframework.org/schema/context"
    xmlns:p="http://www.springframework.org/schema/p"
    xsi:schemaLocation="...">

    <!-- ========================================
         Redis 연결 팩토리
         ======================================== -->
    <bean id="redisConnectionFactory"
          class="org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory"
          p:host-name="${lxp.redis.host}"
          p:port="${lxp.redis.port}"
          p:database="1"/>
    <!--
        p:host-name  : Redis 서버 주소 (properties에서 읽음)
        p:port       : Redis 포트
        p:database   : Redis DB 번호 (0~15)

        ⚠️ 중요: password 프로퍼티가 주석 처리된 이유
        ─────────────────────────────────────────
        문제: Lettuce 연결 풀링 시, 재연결할 때 password 속성을
              다시 참조하지 않는 버그가 있음

        증상: 처음 연결은 성공하나, 연결이 끊겼다가 다시 연결될 때
              인증 실패 발생

        해결: password 대신 네트워크 보안으로 대체
              → Redis는 WAS 서버에서만 접근 가능하도록 방화벽 설정
    -->

    <!-- ========================================
         문자열 직렬화기
         ======================================== -->
    <bean id="stringRedisSerializer"
          class="org.springframework.data.redis.serializer.StringRedisSerializer"/>
    <!--
        역할: Key와 Value를 문자열로 직렬화
        장점:
        - Redis CLI에서 데이터 확인 용이
        - 다른 언어/시스템과 호환성 좋음
        - 디버깅 편리
    -->

    <!-- ========================================
         Pub/Sub 메시지 리스너 컨테이너
         ======================================== -->
    <bean id="redisMessageListener"
          class="org.springframework.data.redis.listener.RedisMessageListenerContainer"
          p:connectionFactory-ref="redisConnectionFactory"/>
    <!--
        역할: Redis Pub/Sub 메시지를 구독하고 리스너에게 전달

        동작 방식:
        1. 특정 채널 구독 등록
        2. 메시지 수신 시 등록된 MessageListener 호출
        3. onMessage() 메서드에서 처리

        사용처:
        - 중복 로그인 알림
        - 시험 강제 종료
        - 학습 중복 방지
    -->

    <!-- ========================================
         RedisTemplate
         ======================================== -->
    <bean id="redisTemplate"
          class="org.springframework.data.redis.core.RedisTemplate"
          p:connectionFactory-ref="redisConnectionFactory"
          p:keySerializer-ref="stringRedisSerializer"
          p:hashKeySerializer-ref="stringRedisSerializer"/>
    <!--
        p:keySerializer       : 일반 Key 직렬화 (String)
        p:hashKeySerializer   : Hash의 Field 직렬화 (String)

        Value Serializer는 기본값 사용:
        → JdkSerializationRedisSerializer (Java 직렬화)

        주의: 객체를 저장할 때 클래스 정보도 함께 저장됨
              → 클래스 변경 시 역직렬화 오류 가능
    -->

</beans>
```

### 2.2 Java Config vs XML Config 비교

!!! tip "Java Config vs XML Config 비교"
    | 항목 | Java Config (HUB 사용) | XML Config (LMS 사용) |
    |------|------------------------|------------------------|
    | **선언** | `@Bean RedisConnectionFactory` | `<bean id="..." class="..." p:host-name=.../>` |
    | **장점** | 타입 안전, IDE 지원, 리팩토링 용이 | 재컴파일 없이 수정, 비개발자도 수정 가능, 설정 분리 |
    | **단점** | 변경 시 재빌드 | 오타 찾기 어려움, IDE 지원 제한적 |

    **현재 프로젝트 선택 이유:**

    - HUB: Spring Boot → Java Config 권장
    - LMS: eGovFramework → XML Config 기본 제공

---

## 3. Redis 연결 풀 설정

### 3.1 연결 풀이란?

!!! note "연결 풀(Connection Pool) 개념"
    **Without Pool (매번 새 연결)**

    ```mermaid
    sequenceDiagram
        participant R as 요청
        participant C as 연결
        participant Redis

        R->>C: 연결 생성
        C->>Redis: 명령 실행
        C->>C: 연결 종료
        Note right of C: 매번 반복 (느림)
    ```

    문제: 연결 생성/종료 비용이 큼 (TCP 핸드셰이크)

    **With Pool (연결 재사용)**

    ```mermaid
    sequenceDiagram
        participant R as 요청
        participant P as Connection Pool
        participant Redis

        R->>P: 연결 대여
        P->>Redis: 명령 실행
        Redis->>P: 응답
        P->>R: 연결 반납 (풀로 복귀)
        Note right of P: 연결 재사용 (빠름)
    ```

    장점: 연결 재사용으로 성능 향상

### 3.2 연결 풀 파라미터 가이드

!!! info "연결 풀 파라미터 설명"
    **max-active (최대 활성 연결)**

    - 동시에 사용할 수 있는 최대 연결 수
    - 현재 설정: 5
    - 초과 요청은 대기
    - 권장 공식: `max-active = (요청 처리 시간 x 초당 요청 수) + 여유분`
    - 예시 계산: 요청당 10ms, 초당 100개 → 10ms x 100 / 1000ms = 1개 + 여유분 = 5개

    **max-idle (최대 유휴 연결)**

    - 사용하지 않아도 유지할 최대 연결 수
    - 현재 설정: 5
    - 보통 max-active와 같거나 약간 낮게

    **min-idle (최소 유휴 연결)**

    - 항상 유지할 최소 연결 수
    - 현재 설정: 3
    - 트래픽 급증 대비 미리 연결 확보

### 3.3 현재 프로젝트 설정 적정성 평가

**현재 HUB 설정:**

| 파라미터 | 평가 |
|----------|------|
| max-active=5 | 적절 (소규모~중규모 트래픽) |
| max-idle=5 | 적절 (max-active와 동일) |
| min-idle=3 | 적절 (빠른 응답 보장) |

**권장 상황별 설정:**

| 트래픽 규모 | max-active | max-idle | min-idle |
|-------------|-----------|----------|----------|
| 소규모 (개발) | 5 | 5 | 2 |
| 중규모 (현재) | 5 | 5 | 3 |
| 대규모 (운영) | 10~20 | 10 | 5 |
| 초대규모 | 50+ | 25 | 10 |

---

## 4. 직렬화(Serialization) 설정

### 4.1 직렬화란?

!!! note "직렬화(Serialization)"
    ```mermaid
    graph LR
        OBJ["Java 객체<br>class User {<br>name='홍길동'<br>age=25<br>}"] -->|직렬화| BYTE["Redis (바이트 저장)<br>01101001...<br>(바이트 배열)"]
        BYTE -->|역직렬화| OBJ
    ```

    **왜 필요한가?**

    - Redis는 바이트 데이터만 저장 가능
    - 네트워크 전송을 위해 객체를 바이트로 변환 필요

### 4.2 직렬화 방식 비교

!!! info "직렬화 방식 비교"
    **1. StringRedisSerializer (현재 HUB 사용)**

    - 문자열을 그대로 저장 / 가장 단순하고 호환성 좋음 / 객체 저장 불가 (문자열만)
    - 예시: `SET "user:1001" "session_abc123"` → Redis에 그대로 저장

    **2. JdkSerializationRedisSerializer (Java 기본)**

    - Java 기본 직렬화 / 클래스 정보 포함 / 용량이 크고 느림
    - 예시: `SET "user:1001" "\xac\xed\x00\x05sr\x00..."` → 사람이 읽기 어려움

    **3. Jackson2JsonRedisSerializer (권장)**

    - JSON 형태로 저장 / 사람이 읽기 쉬움 / 다른 언어와 호환
    - 예시: `SET "user:1001" '{"name":"홍길동","age":25}'` → 가독성 좋음

    **권장 선택:**

    | 용도 | 직렬화 방식 |
    |------|------------|
    | 단순 문자열 | StringRedisSerializer (현재 사용) |
    | 객체 저장 | Jackson2JsonRedisSerializer |
    | 성능 중요 | Kryo, Protobuf |

### 4.3 현재 프로젝트 직렬화 설정

```java
// HUB - RedisConfig.java
redisTemplate.setKeySerializer(new StringRedisSerializer());    // Key: String
redisTemplate.setValueSerializer(new StringRedisSerializer());  // Value: String

// LMS - context-common.xml
p:keySerializer-ref="stringRedisSerializer"      // Key: String
p:hashKeySerializer-ref="stringRedisSerializer"  // Hash Field: String
// Value는 기본값 JdkSerializationRedisSerializer 사용
```

---

## 5. TTL (Time To Live) 설정

### 5.1 TTL 개념

!!! note "TTL (Time To Live)"
    **정의:** 데이터의 유효 시간 (만료 시간)

    ```mermaid
    graph LR
        SAVE["저장"] -->|"TTL: 24시간<br>이 기간 동안만 데이터 유효"| EXPIRE["만료<br>(자동 삭제!)"]
    ```

    **왜 필요한가?**

    - 메모리 절약 (오래된 데이터 자동 정리)
    - 보안 (세션 만료)
    - 캐시 갱신 (오래된 캐시 무효화)

### 5.2 프로젝트별 TTL 설정

!!! example "프로젝트별 TTL 설정"
    **HUB (RedisUtil.java)**

    - TTL: 24시간 (86400초)
    - 슬라이딩 세션: 조회 시마다 TTL 갱신

    ```java
    // 저장 시 24시간 TTL 설정
    redisTemplate.expire(key, 24, TimeUnit.HOURS);

    // 조회 시 TTL 갱신 (슬라이딩 세션)
    if(!retVal.equals("empty")) {
        redisTemplate.expire(key, 24, TimeUnit.HOURS);
    }
    ```

    **LMS (Constants.java)**

    - REDIS_DEFULT_EXPIRE: Properties에서 읽음
    - 모듈별로 다른 TTL 적용 가능

    ```java
    // 상수 정의
    public static final long REDIS_DEFULT_EXPIRE =
        framework.getLong("framework.lxp.redis.defult.expire");

    // 사용
    stringValOps.set(key, value, REDIS_DEFULT_EXPIRE,
                     TimeUnit.SECONDS);
    ```

### 5.3 슬라이딩 세션 vs 고정 세션

!!! tip "슬라이딩 세션 vs 고정 세션"
    **고정 세션 (Fixed Session)**

    ```mermaid
    graph LR
        LOGIN["로그인<br>(저장)"] --> Q1["조회"] --> Q2["조회"] --> EXPIRE["만료"]
    ```

    - TTL: 24시간 (변하지 않음)
    - 특징: 로그인 후 정확히 24시간 후 만료

    **슬라이딩 세션 (Sliding Session) -- 현재 HUB 사용**

    ```mermaid
    graph LR
        LOGIN["로그인<br>(저장)"] -->|"TTL 24h"| Q1["조회1<br>(TTL 갱신)"]
        Q1 -->|"TTL 24h"| Q2["조회2<br>(TTL 갱신)"]
        Q2 -->|"TTL 24h"| Q3["조회3<br>(TTL 갱신)"]
        Q3 -->|"TTL 24h"| CONT["...계속"]
    ```

    - 특징: 활동할 때마다 만료 시간 연장
    - 오랫동안 활동 없으면 만료

---

## 6. Pub/Sub 설정

### 6.1 Pub/Sub 아키텍처

!!! note "Redis Pub/Sub 아키텍처"
    ```mermaid
    graph TD
        WAS1["WAS 1 (Publisher)<br>교수: 시험 종료 버튼"] -->|PUBLISH| REDIS["Redis Server<br>Channel: 'exam_evt'"]
        REDIS -->|subscribe| WAS2["WAS 2 (Subscriber)<br>학생 A 세션"]
        REDIS -->|subscribe| WAS3["WAS 3 (Subscriber)<br>학생 B 세션"]
    ```

    **흐름:**

    1. WAS 1에서 "시험 종료" 이벤트 발행 (PUBLISH)
    2. Redis가 모든 구독자에게 메시지 전파
    3. WAS 2, 3의 Subscriber가 메시지 수신
    4. 각 WAS에서 해당 학생 세션에 알림

### 6.2 LMS Pub/Sub 설정 코드

```xml
<!-- context-common.xml -->

<!-- 메시지 리스너 컨테이너 -->
<bean id="redisMessageListener"
      class="org.springframework.data.redis.listener.RedisMessageListenerContainer"
      p:connectionFactory-ref="redisConnectionFactory"/>

<!--
    역할:
    - Redis 채널 구독 관리
    - 메시지 수신 시 등록된 Listener 호출
    - 비동기로 메시지 처리

    추가 설정 필요 (Java에서):
    - 채널 등록: container.addMessageListener(subscriber, topic)
    - 채널 해제: container.removeMessageListener(subscriber)
-->
```

### 6.3 Pub/Sub 사용 예시 (시험 종료)

```java
// === 1. 교수가 시험 종료 버튼 클릭 (Publisher) ===

@Service
public class ExamService {

    @Autowired
    private ExamRedisPublisher publisher;

    public void stopExam(String examId) {
        // 시험 종료 이벤트 생성
        ExamPubSupVO event = new ExamPubSupVO();
        event.setEventType("STOP");
        event.setExamId(examId);

        // Redis 채널로 발행
        ChannelTopic topic = new ChannelTopic("exam_event");
        publisher.publish(topic, event);
    }
}

// === 2. 모든 WAS의 Subscriber가 메시지 수신 ===

@Service
public class ExamRedisSubscriber implements MessageListener {

    @Autowired
    private ExamSseService examSseService;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        // 메시지 역직렬화
        ExamPubSupVO event = deserialize(message);

        if ("STOP".equals(event.getEventType())) {
            // 해당 시험 응시 중인 학생들에게 SSE 알림
            examSseService.stopRequest(event);
        }
    }
}

// === 3. SSE로 학생 브라우저에 실시간 알림 ===

@Service
public class ExamSseService {

    public void stopRequest(ExamPubSupVO event) {
        // 해당 시험 응시자 목록 조회
        List<SseEmitter> emitters = getEmittersByExamId(event.getExamId());

        // 각 학생에게 종료 알림 전송
        for (SseEmitter emitter : emitters) {
            emitter.send(SseEmitter.event()
                .name("exam-stop")
                .data("시험이 종료되었습니다."));
        }
    }
}
```

---

## 7. 환경별 설정 분리

### 7.1 HUB 환경 분리

!!! note "HUB 환경별 설정"
    **파일 구조:**

    - `application.properties` -- 개발/로컬
    - `application-dev.properties` -- 운영

    **개발 환경** (application.properties):

    ```properties
    spring.redis.host=133.186.251.121
    spring.redis.port=6379
    spring.redis.password=medi-redis8500
    spring.redis.key-prefix=KNU10-HUB-TEST:  # 개발용
    ```

    **운영 환경** (application-dev.properties):

    ```properties
    spring.redis.host=133.186.251.121
    spring.redis.port=6379
    spring.redis.password=medi-redis8500
    spring.redis.key-prefix=KNU10-HUB:       # 운영용
    ```

    **차이점:** 키 접두어만 다름 (데이터 충돌 방지), 같은 Redis 서버 사용

    **Redis 데이터 분리:**

    - 개발: `KNU10-HUB-TEST:user123 = "sess_dev_abc"`
    - 운영: `KNU10-HUB:user123 = "sess_prod_xyz"`
    - 같은 Redis에서도 키가 다르므로 충돌 없음

### 7.2 LMS 환경 분리

!!! note "LMS 환경별 설정"
    **파일 구조:**

    - `framework.properties` -- 환경별 값
    - `context-common.xml` -- 공통 설정 (변수 참조)

    **framework.properties:**

    ```properties
    # Redis 기본 설정
    framework.lxp.redis.site=KNU10-LMS
    framework.lxp.redis.defult.expire=3600
    framework.lxp.redis.host=${lxp.redis.host}
    framework.lxp.redis.port=${lxp.redis.port}
    framework.lxp.redis.auth=${lxp.redis.auth}
    framework.lxp.redis.useyn=${lxp.redis.useyn}
    ```

    **환경별 값 (lxp.* 변수):**

    | 환경 | host | site |
    |------|------|------|
    | 개발 | 133.186.251.121 | KNU10-LMS-DEV |
    | 운영 | 운영서버IP | KNU10-LMS |

    **DB 번호로도 분리 (LMS 특징):**

    - HUB: database=0 (기본값)
    - LMS: database=1
    - 같은 Redis에서 논리적으로 완전 분리 (`SELECT 1` 명령으로 DB 전환)

### 7.3 Redis DB 번호 설명

!!! info "Redis Database 구조"
    Redis는 기본적으로 16개의 논리적 DB를 제공 (0~15)

    | DB 번호 | 용도 | 상태 |
    |---------|------|------|
    | DB 0 | HUB 데이터 | 사용중 |
    | DB 1 | LMS 데이터 | 사용중 |
    | DB 2~15 | - | 미사용 |

    **장점:**

    - 애플리케이션별 데이터 완전 분리
    - 하나의 Redis 서버로 여러 환경 관리
    - FLUSHDB로 특정 DB만 초기화 가능

    **단점:**

    - DB 간 데이터 이동 불편
    - 클러스터 모드에서는 DB 0만 사용 가능

    **현재 사용:**

    - DB 0: HUB (기본값이라 명시적 설정 안 함)
    - DB 1: LMS (`p:database="1"` 명시)

---

**다음 문서**: [04_실제_코드_패턴_분석.md](./04_실제_코드_패턴_분석.md)
