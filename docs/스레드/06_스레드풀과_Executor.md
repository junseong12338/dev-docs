# 06. 스레드풀과 Executor

**이 장의 목표**: 스레드를 직접 만들지 않고 풀(Pool)로 관리하는 이유를 이해한다

---

## 1. 스레드를 매번 만들면 뭐가 문제야?

```
웹 서버에 요청이 1000개 들어오면:

방법 A: 요청마다 새 스레드 생성
  → new Thread() × 1000
  → OS가 스레드 1000개 관리
  → 스레드 생성/소멸 비용 × 1000
  → 메모리 폭발 (스레드 1개당 스택 ~512KB)
  → 512KB × 1000 = 500MB 스택만으로

방법 B: 스레드 미리 만들어놓고 재사용 (스레드풀)
  → 스레드 50개 미리 생성
  → 요청 들어오면 빈 스레드에 할당
  → 처리 끝나면 스레드 반납 (죽이지 않음)
  → 다음 요청에 재사용
```

!!! example "비유"

    **방법 A** = 택시 필요할 때마다 택시 공장에서 새로 만듦. 다 타면 택시 폐차. 비용 미침.

    **방법 B** = 택시 회사에 택시 50대 보유. 손님 오면 빈 택시 배정. 손님 내리면 택시 대기. 효율적.

---

## 2. ExecutorService

Java 5부터 제공하는 **스레드풀 관리 인터페이스**

### 2.1 기본 사용법

```java
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

// 스레드풀 생성 (스레드 10개)
ExecutorService pool = Executors.newFixedThreadPool(10);

// 작업 제출 (스레드풀이 알아서 빈 스레드에 할당)
pool.submit(() -> {
    System.out.println("작업 실행: " + Thread.currentThread().getName());
});

// 종료
pool.shutdown();  // 진행 중인 작업 완료 후 종료
```

### 2.2 스레드풀 종류

!!! note "스레드풀 종류"

    **newFixedThreadPool(n):**
    고정 크기 n개. 모든 스레드 사용 중이면 큐에서 대기. 용도: 안정적인 동시 처리 필요할 때

    **newCachedThreadPool():**
    필요할 때 생성, 60초 안 쓰면 제거. 용도: 짧은 작업 많을 때. 주의: 작업 폭주하면 스레드 무한 생성 -- OOM 위험

    **newSingleThreadExecutor():**
    스레드 1개. 작업을 순서대로 처리. 용도: 순서 보장 필요할 때

    **newScheduledThreadPool(n):**
    Timer의 상위 호환. 스레드 n개로 예약 실행. 용도: Timer 대신 사용 (더 안전)

---

## 3. ScheduledExecutorService — Timer의 대안

### 3.1 Timer vs ScheduledExecutorService

!!! tip "Timer vs ScheduledExecutorService"

    **Timer:**

    - 스레드 1개
    - 작업에서 예외 터지면 Timer 전체 죽음
    - 시스템 시간 변경에 영향 받음
    - Java 1.3부터 (오래됨)

    **ScheduledExecutorService:**

    - 스레드 여러 개 가능
    - 예외 터져도 다른 작업에 영향 없음
    - 상대 시간 사용 가능 (더 정확)
    - Java 5부터 (권장)

### 3.2 사용 예시

```java
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(1);

// 1초 후 시작, 1초 간격으로 반복
scheduler.scheduleAtFixedRate(() -> {
    System.out.println("1초마다 실행");
}, 0, 1, TimeUnit.SECONDS);

// 종료
scheduler.shutdown();
```

```
만약 우리 코드를 Timer 대신 ScheduledExecutorService로 바꾼다면?
→ 예외 안전성은 올라가지만
→ 여전히 1초마다 리플렉션 → DelegatingClassLoader 누적
→ 근본적 해결 아님

진짜 해결: 감시 기능 자체를 제거 (SqlSessionFactoryBean으로 교체)
```

---

## 4. Tomcat의 스레드풀

!!! note "Tomcat 스레드풀 구조"

    **Tomcat server.xml 설정:**

    ```xml
    <Connector port="8080"
               maxThreads="200"
               minSpareThreads="25"
               acceptCount="100" />
    ```

    | 속성 | 값 | 의미 |
    |------|-----|------|
    | maxThreads | 200 | 최대 스레드 수 |
    | minSpareThreads | 25 | 최소 유지 스레드 수 |
    | acceptCount | 100 | 대기 큐 크기 |

    **동작:**

    1. 서버 시작 -- 스레드 25개 미리 생성
    2. 요청 들어옴 -- 빈 스레드에 할당
    3. 스레드 부족 -- 새로 생성 (최대 200개까지)
    4. 200개 다 사용 중 -- 대기 큐(100개)에서 줄 서기
    5. 대기 큐도 가득 참 -- 요청 거부 (503 에러)
    6. 요청 처리 완료 -- 스레드 반납 (재사용)

    **우리 서버:** http-nio-8080-exec-1 ~ exec-200 이게 Tomcat 스레드풀의 스레드들

---

## 5. 스레드풀 크기 정하기

!!! tip "스레드풀 크기 가이드"

    **CPU 집약적 작업** (계산, 암호화): 스레드 수 = CPU 코어 수 + 1 (더 많으면 컨텍스트 스위칭 비용만 증가)

    **I/O 집약적 작업** (DB 조회, 파일 읽기, HTTP 호출): 스레드 수 = CPU 코어 수 x (1 + 대기시간/실행시간) (I/O 대기하는 동안 다른 스레드가 CPU 쓸 수 있으니까)

    **웹 서버 (Tomcat):** 보통 100~200개. 대부분 I/O 작업(DB 조회)이니까 많아도 됨

---

## 6. 핵심 정리

!!! abstract "핵심 정리"

    **스레드풀(Thread Pool):** 스레드를 미리 만들어놓고 재사용. 생성/소멸 비용 절약. 동시 스레드 수 제한으로 안정성 확보.

    **ExecutorService:** Java 5+ 표준 스레드풀 인터페이스. submit()으로 작업 제출, shutdown()으로 종료.

    **ScheduledExecutorService:** Timer의 상위 호환. 예외 안전, 멀티 스레드.

    **Tomcat 스레드풀:** maxThreads=200 (최대 동시 처리). 우리 서버의 http-nio-* 스레드들.

    **다음 장:** 데몬 스레드와 GC -- 스레드가 메모리 누수의 원인이 되는 메커니즘
