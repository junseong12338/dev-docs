# Redis 기본 개념 완벽 가이드

**작성일**: 2025-12-17
**대상**: 신입 개발자 및 Redis 입문자
**난이도**: ★☆☆☆☆ ~ ★★★☆☆

---

## 목차
1. [Redis란 무엇인가?](#1-redis란-무엇인가)
2. [왜 Redis를 사용하는가?](#2-왜-redis를-사용하는가)
3. [Redis의 핵심 특징](#3-redis의-핵심-특징)
4. [Redis 데이터 타입](#4-redis-데이터-타입)
5. [Redis vs 기존 데이터베이스](#5-redis-vs-기존-데이터베이스)
6. [Redis 아키텍처](#6-redis-아키텍처)
7. [실무에서의 Redis 활용 사례](#7-실무에서의-redis-활용-사례)

---

## 1. Redis란 무엇인가?

### 1.1 정의

**Redis**는 **RE**mote **DI**ctionary **S**erver의 약자입니다.

!!! abstract "Redis"
    **"메모리 기반의 Key-Value 데이터 저장소"**

    ```mermaid
    graph LR
        Key["Key<br>'user1'"] --> Value["Value<br>'홍길동'"]
        Speed["초고속<br>접근"] --> Value
    ```

### 1.2 쉽게 이해하기

**비유: 도서관 vs 책상**

| 구분 | 일반 DB (MySQL, Oracle) | Redis |
|------|------------------------|-------|
| 비유 | 도서관 창고 | 책상 위 메모장 |
| 저장 위치 | 하드디스크 (영구 저장) | 메모리 (RAM) |
| 속도 | 느림 (창고에서 찾아옴) | 매우 빠름 (바로 앞에 있음) |
| 용량 | 큼 (TB 단위) | 작음 (GB 단위) |
| 데이터 유지 | 전원 꺼져도 유지 | 전원 꺼지면 사라질 수 있음 |

!!! example "실생활 예시"
    **도서관 (MySQL)**

    - 책을 찾으러 창고까지 가야 함
    - 시간이 걸리지만 수만 권 보관 가능
    - 영구 보존

    **책상 메모장 (Redis)**

    - 자주 쓰는 내용은 책상 위에 메모
    - 바로 볼 수 있음 (초고속)
    - 공간이 한정적
    - 메모장 없어지면 내용도 사라짐

### 1.3 Redis의 탄생 배경

!!! info "Redis의 탄생 배경"
    - **2009년**: Salvatore Sanfilippo가 이탈리아에서 개발
    - **문제**: 웹 애플리케이션에서 DB 조회가 너무 느림
    - **해결**: 자주 사용하는 데이터를 메모리에 저장하자!

    > "모든 데이터를 DB에서 매번 가져오지 말고, 자주 쓰는 건 메모리에 캐싱하자!"

---

## 2. 왜 Redis를 사용하는가?

### 2.1 성능 비교 (실제 수치)

!!! tip "응답 시간 비교"
    ```
    MySQL 조회    ████████████████████████████████  ~10ms

    Redis 조회    ██  ~0.1ms

    → Redis가 약 100배 빠름!
    ```

### 2.2 실제 사용 시나리오

```java
// ❌ 비효율적인 방식 (매번 DB 조회)
public User getUser(String userId) {
    // 매 요청마다 DB 조회 → 느림
    return userRepository.findById(userId);
}

// ✅ 효율적인 방식 (Redis 캐싱)
public User getUser(String userId) {
    // 1. Redis에서 먼저 찾기
    User cachedUser = redisTemplate.opsForValue().get("user:" + userId);

    if (cachedUser != null) {
        return cachedUser;  // 캐시 히트! 초고속 반환
    }

    // 2. 없으면 DB에서 조회
    User user = userRepository.findById(userId);

    // 3. 다음을 위해 Redis에 저장
    redisTemplate.opsForValue().set("user:" + userId, user);

    return user;
}
```

### 2.3 Redis를 사용하면 좋은 상황

| 상황 | 설명 | 예시 |
|------|------|------|
| **세션 관리** | 로그인 상태 저장 | 사용자 로그인 정보 |
| **캐싱** | 자주 조회하는 데이터 | 인기 상품 목록 |
| **실시간 데이터** | 빠른 읽기/쓰기 | 실시간 랭킹, 좋아요 수 |
| **중복 방지** | 동시 접근 제어 | 중복 로그인 방지 |
| **메시지 큐** | 비동기 처리 | 알림 발송, 작업 큐 |

---

## 3. Redis의 핵심 특징

### 3.1 In-Memory 저장

!!! note "데이터 저장 위치"
    ```mermaid
    graph TD
        CPU1["CPU"] --> RAM1["RAM (메모리)<br>⚡ 초고속 접근<br><b>Redis 여기!</b>"]
        RAM1 --> HDD1["HDD/SSD<br>느린 접근"]

        CPU2["CPU"] --> RAM2["RAM (메모리)<br>⚡ 초고속 접근"]
        RAM2 --> HDD2["HDD/SSD<br>느린 접근<br><b>MySQL 여기!</b>"]
    ```

### 3.2 Single Thread 모델

Redis의 특징: 단일 스레드로 동작

!!! success "장점"
    - 동시성 문제 없음 (Lock 불필요)
    - 구현이 단순
    - Atomic 연산 보장

!!! question "왜 빠른가?"
    - 메모리 접근이라 CPU 부하 적음
    - 컨텍스트 스위칭 오버헤드 없음
    - 네트워크 I/O가 병목 (CPU가 아님)

### 3.3 데이터 영속성 (Persistence)

Redis도 데이터를 디스크에 저장할 수 있음!

!!! note "영속성 옵션"
    **1. RDB (Redis Database)**

    - 특정 시점의 스냅샷 저장
    - 예: 1시간마다 전체 데이터 백업
    - 장점: 복구 빠름 / 단점: 데이터 유실 가능

    **2. AOF (Append Only File)**

    - 모든 쓰기 명령을 로그로 기록
    - 예: SET user1 "홍길동" 명령 자체를 저장
    - 장점: 데이터 안전 / 단점: 파일 크기 큼

    **3. 혼합 사용 (권장)**

    - RDB + AOF 함께 사용

### 3.4 TTL (Time To Live)

데이터에 유효기간을 설정할 수 있음

!!! example "TTL 설정 예시"
    ```redis
    SET session:user123 "login_data" EX 3600
    ```

    **의미**: session:user123 키에 "login_data" 저장, 3600초(1시간) 후 자동 삭제

**실제 활용:**

| 용도 | TTL 예시 | 설명 |
|------|----------|------|
| 로그인 세션 | 24시간 | 하루 후 자동 로그아웃 |
| OTP 인증번호 | 3분 | 3분 후 만료 |
| 캐시 데이터 | 1시간 | 1시간마다 갱신 |
| API Rate Limit | 1분 | 분당 요청 수 제한 |

---

## 4. Redis 데이터 타입

### 4.1 String (문자열)

가장 기본적인 타입. Key-Value 1:1 매핑

!!! note "명령어 예시"
    ```redis
    SET user:1001 "홍길동"        # 저장
    GET user:1001                 # 조회 → "홍길동"

    SET counter 100               # 숫자도 문자열로 저장
    INCR counter                  # 1 증가 → 101
    DECR counter                  # 1 감소 → 100
    ```

    **Java 코드:**

    ```java
    redisTemplate.opsForValue().set("user:1001", "홍길동");
    String name = redisTemplate.opsForValue().get("user:1001");
    ```

### 4.2 Hash (해시)

하나의 Key에 여러 필드-값 쌍 저장 (객체 저장에 적합)

!!! note "Key: user:1001"
    | Field | Value |
    |-------|-------|
    | name | "홍길동" |
    | email | "hong@example.com" |
    | age | "25" |
    | department | "개발팀" |

    **명령어:**

    ```redis
    HSET user:1001 name "홍길동" email "hong@example.com"
    HGET user:1001 name              # → "홍길동"
    HGETALL user:1001                # → 전체 필드-값
    ```

    **Java 코드:**

    ```java
    Map<String, Object> userMap = new HashMap<>();
    userMap.put("name", "홍길동");
    userMap.put("email", "hong@example.com");
    hashOperations.putAll("user:1001", userMap);
    ```

### 4.3 List (리스트)

순서가 있는 문자열 목록 (Queue, Stack 구현 가능)

!!! note "Key: notification:user1001"
    | 인덱스 | 0 | 1 | 2 | 3 | 4 |
    |--------|------|------|------|------|------|
    | 값 | 알림1 | 알림2 | 알림3 | 알림4 | 알림5 |

    - **LPUSH**: 왼쪽에 추가 (최신 알림을 맨 앞에)
    - **RPUSH**: 오른쪽에 추가
    - **LPOP**: 왼쪽에서 꺼내기
    - **RPOP**: 오른쪽에서 꺼내기

    **Java 코드:**

    ```java
    listOperations.leftPush("notifications", "새 알림!");
    List<Object> notifications = listOperations.range("notifications", 0, -1);
    ```

### 4.4 Set (집합)

중복 없는 문자열 집합

!!! note "Key: course:CS101:students"
    `{ "학생A", "학생B", "학생C", "학생D" }`

    **특징:**

    - 중복 자동 제거
    - 순서 없음
    - 집합 연산 가능 (교집합, 합집합, 차집합)

    **활용:** 태그, 팔로워 목록, 좋아요한 사용자 등

### 4.5 Sorted Set (정렬된 집합)

점수(Score)로 정렬된 집합 → 랭킹에 최적

!!! note "Key: game:leaderboard"
    | Member | Score | Rank |
    |--------|-------|------|
    | player1 | 9500 | 1 |
    | player2 | 8700 | 2 |
    | player3 | 8200 | 3 |
    | player4 | 7800 | 4 |

    자동으로 점수 순 정렬!

---

## 5. Redis vs 기존 데이터베이스

### 5.1 비교표

| 특성 | Redis | MySQL/Oracle |
|------|-------|--------------|
| **데이터 저장** | 메모리 (RAM) | 디스크 (HDD/SSD) |
| **속도** | 매우 빠름 (~0.1ms) | 느림 (~10ms) |
| **데이터 모델** | Key-Value | 관계형 (테이블) |
| **쿼리 언어** | 단순 명령어 | SQL |
| **용량** | 제한적 (RAM 크기) | 거의 무제한 |
| **복잡한 쿼리** | 불가능 | 가능 (JOIN 등) |
| **트랜잭션** | 제한적 | 완전 지원 |
| **데이터 안전성** | 설정에 따라 다름 | 높음 |

### 5.2 언제 무엇을 사용할까?

!!! tip "사용 시나리오"
    **Redis 사용 (빠른 접근 필요)**

    - 세션 저장 (로그인 상태)
    - 캐싱 (자주 조회하는 데이터)
    - 실시간 데이터 (조회수, 좋아요)
    - 메시지 큐 (비동기 작업)
    - Rate Limiting (API 호출 제한)

    **MySQL/Oracle 사용 (영구 저장 필요)**

    - 사용자 정보 (회원 데이터)
    - 주문 내역 (거래 기록)
    - 복잡한 검색 (조건 조회)
    - 데이터 분석 (통계, 리포트)

    보통 함께 사용! (Redis = 캐시, DB = 영구 저장)

---

## 6. Redis 아키텍처

### 6.1 기본 구조

!!! note "Redis 기본 아키텍처"
    ```mermaid
    graph TD
        C1["Client 1<br>(WAS 1)"] --> RS["Redis Server"]
        C2["Client 2<br>(WAS 2)"] --> RS
        C3["Client 3<br>(WAS 3)"] --> RS

        subgraph RS_DETAIL["Redis Server"]
            MEM["Memory<br>Key1 | Key2 | Key3"]
            PERSIST["Persistence<br>(RDB/AOF)"]
        end

        RS --> MEM
        MEM --> PERSIST
    ```

### 6.2 Pub/Sub 구조

!!! note "Redis Pub/Sub (발행/구독) 모델"
    ```mermaid
    graph TD
        WAS1["WAS 1<br>(Publisher)"] -->|publish| CH["Redis Channel<br>'알림채널'"]
        CH -->|subscribe| WAS2["WAS 2<br>(Subscriber)"]
        CH -->|subscribe| WAS3["WAS 3<br>(Subscriber)"]
        CH -->|subscribe| WAS4["WAS 4<br>(Subscriber)"]
    ```

    - 예: WAS1에서 "로그인 중복" 이벤트 발행
    - 모든 WAS가 메시지 수신
    - 해당 사용자 세션 처리

---

## 7. 실무에서의 Redis 활용 사례

### 7.1 세션 관리 (중복 로그인 방지)

시나리오: 사용자가 다른 브라우저에서 로그인하면 기존 세션 종료

!!! example "중복 로그인 방지 흐름"
    **1. 사용자 A가 PC에서 로그인**

    - Redis: `SET user:A "session_id_123"`

    **2. 사용자 A가 모바일에서 다시 로그인**

    - Redis: `SET user:A "session_id_456"` (덮어쓰기)

    **3. PC에서 요청 시**

    - Redis에서 user:A 조회 → `"session_id_456"`
    - 현재 세션 `"session_id_123"` ≠ Redis 값
    - 로그아웃 처리!

### 7.2 실시간 데이터 캐싱

시나리오: 인기 강좌 목록을 매번 DB에서 조회하지 않음

!!! example "실시간 데이터 캐싱"
    **Before (Redis 없음)**

    요청 100개 → DB 조회 100번 → 느림

    **After (Redis 캐싱)**

    요청 100개 → Redis 조회 100번 → 빠름 (1분마다 DB에서 갱신)

    **코드 흐름:**

    ```
    if (Redis에 데이터 있음?) {
        return Redis 데이터;  // 캐시 히트
    } else {
        data = DB 조회;       // 캐시 미스
        Redis에 저장 (TTL 60초);
        return data;
    }
    ```

### 7.3 분산 환경 메시지 전달

시나리오: 여러 WAS 서버에서 실시간 알림 동기화

!!! example "분산 환경 메시지 전달"
    ```mermaid
    graph TD
        WAS1["WAS 1<br>user A"] --> REDIS["Redis Pub/Sub<br>Channel: 'exam_event'"]
        WAS2["WAS 2<br>user B"] --> REDIS
        WAS3["WAS 3<br>user C"] --> REDIS
        REDIS --> WAS1
        REDIS --> WAS2
        REDIS --> WAS3
    ```

    1. 교수가 시험 종료 버튼 클릭 (WAS 1)
    2. Redis로 "시험종료" 메시지 발행
    3. 모든 WAS가 수신
    4. 각 WAS에서 해당 학생들에게 알림 전송

---

## 핵심 정리

!!! abstract "Redis 핵심 정리"
    **1. Redis = 메모리 기반 초고속 Key-Value 저장소**

    **2. 주요 용도:**

    - 세션 관리 (로그인 상태)
    - 캐싱 (자주 조회하는 데이터)
    - 실시간 메시징 (Pub/Sub)
    - 중복 방지 (동시 접근 제어)

    **3. 핵심 특징:**

    - 초고속 (메모리 저장)
    - TTL 지원 (자동 만료)
    - 다양한 데이터 타입
    - Pub/Sub 메시징

    **4. 주의사항:**

    - 메모리 용량 제한
    - 영속성 설정 필요
    - 영구 데이터는 DB에 저장

---

**다음 문서**: [02_프로젝트별_Redis_적용현황.md](./02_프로젝트별_Redis_적용현황.md)
