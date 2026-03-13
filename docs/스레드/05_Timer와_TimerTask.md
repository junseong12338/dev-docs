# 05. Timer와 TimerTask

**이 장의 목표**: Timer가 어떻게 동작하는지 이해하고, 왜 메모리 누수 원인이 되는지 안다

---

## 1. Timer란

`java.util.Timer` = **스레드 1개로 예약된 작업을 반복 실행**하는 도구

```java
Timer timer = new Timer();           // Timer 스레드 생성
timer.schedule(task, delay, period); // 작업 예약
```

```
비유:
  Timer = 알람 시계
  TimerTask = 알람이 울리면 할 일
  schedule = "몇 초 후에, 몇 초 간격으로 울려줘"
```

---

## 2. TimerTask란

`java.util.TimerTask` = Timer가 실행할 작업을 정의하는 추상 클래스

```java
TimerTask task = new TimerTask() {
    @Override
    public void run() {
        // 이 안에 반복할 작업을 적는다
        System.out.println("1초마다 실행됨");
    }
};
```

---

## 3. Timer 사용법

### 3.1 기본 사용

```java
Timer timer = new Timer();

// 1회 실행: 3초 후에 한 번만
timer.schedule(task, 3000);

// 반복 실행: 0초 후 시작, 1초 간격으로 반복
timer.schedule(task, 0, 1000);

// 취소
timer.cancel();
```

### 3.2 schedule 파라미터

```
timer.schedule(task, delay, period)
                │      │      │
                │      │      └─ 반복 간격 (밀리초). 1000 = 1초
                │      └─ 최초 실행까지 대기 시간. 0 = 즉시
                └─ 실행할 작업 (TimerTask)
```

### 3.3 Timer 생성자

```java
new Timer()          // 일반 스레드로 생성 (이름: Timer-0)
new Timer(true)      // 데몬 스레드로 생성 (이름: Timer-0)
new Timer("이름")    // 이름 지정
new Timer("이름", true)  // 이름 + 데몬
```

---

## 4. Timer 내부 동작

### 4.1 Timer 안에는 스레드가 1개 있다

!!! note "Timer 내부 구조"

    **Timer 객체**

    - **TaskQueue** (작업 큐)
        - TimerTask 목록 (예약된 작업들)
    - **TimerThread** (스레드 1개)
        - 무한 루프:
            1. 큐에서 다음 작업 꺼냄
            2. 실행 시간 됐으면 task.run() 실행
            3. 안 됐으면 wait(남은시간)
            4. 반복 작업이면 다시 큐에 넣음
            5. 1번으로

### 4.2 TimerThread의 실제 루프 (JDK 소스 요약)

```java
// java.util.Timer 내부 TimerThread
class TimerThread extends Thread {
    TaskQueue queue;

    public void run() {
        while (true) {           // ← 무한 루프!
            TimerTask task;
            synchronized(queue) {
                while (queue.isEmpty())
                    queue.wait();         // 작업 없으면 대기

                task = queue.getMin();     // 가장 빠른 작업 꺼냄
                long wait = task.nextExecutionTime - System.currentTimeMillis();

                if (wait > 0)
                    queue.wait(wait);      // 실행 시간까지 대기
                else
                    task.run();            // 실행!
            }
        }
    }
}
```

```
핵심: while(true) → 무한 루프
→ timer.cancel() 호출하거나 JVM 종료 전까지 이 스레드는 안 죽는다
```

---

## 5. 우리 코드 완전 해부

### 5.1 코드

```java
// RefreshableSqlSessionFactoryBean.java

// 1. TimerTask 정의
task = new TimerTask() {
    private Map<Resource, Long> map = new HashMap<>();  // 파일별 수정시간 기록

    public void run() {
        if (isModified()) {     // 파일 변경 확인
            refresh();          // 변경됐으면 SqlSessionFactory 재빌드
        }
    }

    private boolean isModified() {
        for (int i = 0; i < mapperLocations.length; i++) {   // 126개 순회
            Resource mappingLocation = mapperLocations[i];
            findModifiedResource(mappingLocation);  // 각 파일 수정시간 체크
        }
        // ...
    }
};

// 2. Timer 생성 + 실행
timer = new Timer(true);       // Timer-0 스레드 생성 (데몬)
resetInterval();                // → timer.schedule(task, 0, 1000)
```

### 5.2 실행 흐름

```
서버 시작
  ↓
new Timer(true)
  → Timer-0 스레드 생성
  → while(true) 루프 시작
  ↓
timer.schedule(task, 0, 1000)
  → task를 큐에 넣음
  → 즉시(0ms) 첫 실행
  ↓
Timer-0: task.run() 실행
  → isModified() 호출
  → mapperLocations 126개 순회
  → 각 파일의 lastModified() 체크 (리플렉션 발생!)
  → 변경 없으면 아무것도 안 함
  ↓
Timer-0: 1초 대기 (TIMED_WAITING)
  ↓
Timer-0: task.run() 실행 (또)
  → 126개 순회 (또)
  → 리플렉션 (또)
  → DelegatingClassLoader 생성 (또)
  ↓
... 무한 반복 ...
  ↓
5일 후: DelegatingClassLoader 4,257개 누적
```

### 5.3 참조 관계

```
Timer-0 (GC Root: 살아있는 스레드)
  ↓ 스레드가 들고 있는 TaskQueue
TimerTask (task 변수)
  ↓ task 안에 있는 외부 참조
RefreshableSqlSessionFactoryBean (this)
  ↓ 필드
mapperLocations (Resource[126])
  ↓ 리플렉션 접근 시 생성
리플렉션 캐시
  ↓ 캐시 안의 ClassLoader
DelegatingClassLoader × 4,257개

→ Timer-0이 살아있는 한 이 체인 전부 GC 불가
```

---

## 6. Timer.cancel()

```java
// Timer 중지
timer.cancel();

// 이러면:
// 1. TaskQueue 비움
// 2. TimerThread의 while 루프 종료
// 3. Timer-0 스레드 TERMINATED
// 4. 참조 체인 끊김 → GC 가능
```

```
우리 코드의 destroy():

public void destroy() throws Exception {
    timer.cancel();  // Bean 소멸 시 Timer 정리
}

→ 서버 정상 종료 시 호출됨
→ 하지만 서버가 돌아가는 동안에는 Timer-0은 계속 살아있음
→ 5일, 10일, 30일... 계속 누적
```

---

## 7. Timer의 한계와 대안

!!! danger "Timer의 문제점"

    1. 스레드 1개 -- 작업 하나가 오래 걸리면 다음 작업 밀림
    2. 예외 터지면 Timer 전체 죽음
    3. 시간 정확도 낮음 (시스템 시간에 의존)

    **대안: ScheduledExecutorService (Java 5+)**

    - 스레드 풀 사용
    - 예외 처리 개선
    - 더 정확한 스케줄링

    하지만 우리 케이스에서는 대안을 적용할 필요가 없다. 파일 감시 기능 자체가 불필요하니까.
    SqlSessionFactoryBean(부모)으로 교체 = 기능 자체 제거

---

## 8. 핵심 정리

!!! abstract "핵심 정리"

    **Timer:**

    - 내부에 스레드 1개 (TimerThread)
    - while(true) 무한 루프로 작업 반복 실행
    - cancel() 호출 전까지 스레드 안 죽음

    **TimerTask:**

    - Timer가 실행할 작업 정의
    - run() 메서드에 로직 작성

    **우리 서버 문제:** timer.schedule(task, 0, 1000) -- 1초마다 126개 파일 체크 -- 리플렉션 -- DelegatingClassLoader 생성 -- Timer-0이 참조 잡음 -- GC 불가 -- 누적

    **해결:** Timer 자체를 안 만들면 됨 -- SqlSessionFactoryBean(부모 클래스)으로 교체 -- Timer 없음 -- 스레드 없음 -- 누적 없음

    **다음 장:** 스레드풀과 Executor -- 스레드를 더 똑똑하게 관리하는 방법
