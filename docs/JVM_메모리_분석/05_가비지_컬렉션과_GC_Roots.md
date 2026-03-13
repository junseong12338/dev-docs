# 05. 가비지 컬렉션(GC)과 GC Roots

**이 장의 목표**: "Number of GC roots 5,863"이 뭔지, GC가 어떻게 동작하는지 이해한다

---

## 1. 가비지(Garbage)란

### 1.1 개념

```
가비지 = 더 이상 아무도 사용하지 않는 객체

Java에서는 개발자가 직접 메모리를 해제하지 않는다.
(C/C++은 free(), delete 직접 호출해야 함)

Java는 GC(Garbage Collector)가 알아서 해준다.
```

```java
// 가비지가 생기는 예시

User user = new User("이준성");   // User 객체 생성 (힙에 살아있음)
user = null;                      // user가 더 이상 객체를 가리키지 않음
                                  // → User 객체는 가비지가 됨
                                  // → GC가 나중에 회수함

User a = new User("김철수");      // 객체 A 생성
User b = new User("박영희");      // 객체 B 생성
a = b;                            // a가 이제 B를 가리킴
                                  // → 객체 A는 아무도 안 가리킴
                                  // → 객체 A는 가비지
```

```
비유:
  사무실에 서류(객체)가 쌓여 있다.
  어떤 서류는 누군가 아직 쓰고 있고 (참조 있음)
  어떤 서류는 아무도 안 쓴다 (참조 없음 = 가비지)

  GC = 청소부
  → 아무도 안 쓰는 서류를 찾아서 파쇄기에 넣음
  → 공간 확보
```

---

## 2. GC는 어떻게 "안 쓰는 객체"를 찾는가

### 2.1 핵심: 도달 가능성 (Reachability)

GC는 "이 객체에 도달할 수 있는가?"로 판단한다.

!!! note "GC의 판단 기준"
    **도달 가능 (Reachable):**

    - 누군가(GC Root에서 시작해서) 이 객체를 찾아갈 수 있음
    - 살려둠

    **도달 불가 (Unreachable):**

    - GC Root에서 시작해서 어떤 경로로도 도달 불가
    - 가비지! → 메모리 회수

### 2.2 GC Root에서 시작하는 탐색

```
GC Root (시작점)
    │
    ├── 객체 A (도달 가능 → 살림)
    │     ├── 객체 B (도달 가능 → 살림)
    │     └── 객체 C (도달 가능 → 살림)
    │           └── 객체 D (도달 가능 → 살림)
    │
    └── 객체 E (도달 가능 → 살림)

    객체 F ← 아무도 참조 안 함 (도달 불가 → 가비지!)
    객체 G ← F만 참조했는데 F도 가비지 (도달 불가 → 가비지!)
```

```
비유:
  GC Root = 전기 콘센트
  참조 = 전선
  객체 = 전자기기

  콘센트(GC Root)에서 전선(참조)을 따라가서
  연결된 기기(객체)는 전원(메모리) 유지.
  전선 끊어진 기기는 전원 차단(GC 회수).
```

---

## 3. GC Root란 정확히 무엇인가

### 3.1 GC Root의 종류

GC Root = "절대 가비지가 아닌, 탐색의 시작점"

!!! note "GC Root 종류"
    **1. 스레드 스택의 지역 변수 (Local Variables)**

    - 현재 실행 중인 메서드의 지역 변수
    - 메서드가 끝나면 사라짐
    - 예: `public void process() { User user = new User(); }` -- user는 메서드 실행 중 GC Root, 메서드 끝나면 제거

    **2. 활성 스레드 (Active Threads)**

    - 살아있는 스레드 자체가 GC Root
    - 스레드가 참조하는 모든 객체가 보호됨
    - 예: Timer-0 스레드가 살아있음 → TimerTask 보호 → 리플렉션 캐시 보호 → DelegatingClassLoader 보호 → **이게 바로 우리 서버의 메모리 누수 원인!**

    **3. static 변수 (Class Variables)**

    - 클래스의 static 필드
    - 클래스가 언로드될 때까지 살아있음
    - 예: `static Map<String, Object> cache = new HashMap<>()` -- cache는 GC Root → cache 안의 모든 객체 보호

    **4. JNI 참조 (Native References)**

    - C/C++ 네이티브 코드가 참조하는 Java 객체
    - 네이티브 코드가 해제할 때까지 유지

    **5. 시스템 클래스 (System Classes)**

    - String, Thread, ClassLoader 등
    - JVM이 기본으로 로드하는 클래스
    - JVM이 살아있는 한 절대 GC 안 됨

    **6. Monitor 객체 (Synchronized)**

    - synchronized 블록에서 사용 중인 객체
    - 락이 풀릴 때까지 GC 안 됨

### 3.2 우리 서버: GC Roots 5,863개

```
GC Root 5,863개 = 탐색 시작점이 5,863개

구성 (추정):
  활성 스레드:        수십 개 (Tomcat 스레드 풀, Timer, APM 등)
  스레드별 지역 변수: 수천 개 (스레드 수 x 메서드 깊이)
  static 변수:        수백 개 (프레임워크 + 라이브러리)
  시스템 클래스:       수백 개
  JNI 참조:           수십 개
  Monitor:            수십 개

정상 범위: 2,000 ~ 10,000개 (애플리케이션 규모에 따라 다름)
우리 서버: 5,863개 → 정상 범위 내
```

---

## 4. GC 동작 방식

### 4.1 Mark and Sweep (표시 후 쓸기)

가장 기본적인 GC 알고리즘:

!!! example "Mark and Sweep"
    **Phase 1: Mark (표시)**

    - GC Root에서 시작
    - 참조 따라가며 도달 가능한 객체에 "살아있음" 표시
    - GC Root → [A (표시)] → [B (표시)] → [C (표시)]
    - [D (미표시)]  [E (미표시)]

    **Phase 2: Sweep (쓸기)**

    - 표시 안 된 객체를 메모리에서 제거
    - [A (살림)] [B (살림)] [C (살림)]
    - [D (제거)] [E (제거)] → 메모리 해제!

    **Phase 3: Compact (선택적)**

    - 살아남은 객체를 한쪽으로 모아서 메모리 단편화 해소
    - Before: `[A][빈][B][빈][빈][C]`
    - After:  `[A][B][C][빈][빈][빈]`

### 4.2 Stop-The-World (STW)

!!! danger "Stop-The-World"
    GC가 실행되면 **모든 애플리케이션 스레드가 멈춘다.**

    **왜?** GC가 객체 참조를 추적하는 동안 다른 스레드가 참조를 바꾸면 꼬이니까 → "다들 잠깐 멈춰!" (Stop-The-World) → GC 작업 완료 → "다시 움직여!" (Resume)

    **문제:**

    - STW 시간 = 서비스 응답 지연
    - Minor GC: 수 ms ~ 수십 ms (짧음)
    - Full GC: 수백 ms ~ 수 초 (길면 서비스 장애)

    **비유:** 고속도로에서 청소하려면 차를 다 세워야 함. 청소 빨리 끝내야 교통 체증 안 생김. Full GC = 전체 도로 청소 (오래 걸림), Minor GC = 일부 구간만 청소 (금방 끝남)

### 4.3 Minor GC vs Full GC

```
Minor GC (Young Generation GC):
  대상: Young 영역 (Eden + Survivor)
  빈도: 자주 (수 초 ~ 수십 초마다)
  시간: 빠름 (수 ms ~ 수십 ms)
  이유: 새 객체 대부분은 금방 죽으니까 (약 95%)

Full GC (Major GC):
  대상: 전체 힙 (Young + Old)
  빈도: 드묾
  시간: 느림 (수백 ms ~ 수 초)
  이유: Old 영역이 가득 찼을 때
  위험: STW가 길어서 서비스에 영향
```

---

## 5. 참조(Reference)의 종류

### 5.1 4가지 참조 강도

GC가 객체를 회수할지 말지는 **참조 강도**에 따라 달라진다.

!!! note "참조 강도 (강 → 약)"
    **1. Strong Reference (강한 참조)** -- 기본값

    - `User user = new User();`
    - 절대 GC 안 됨 (명시적으로 null 넣어야 함)

    **2. Soft Reference (부드러운 참조)**

    - `SoftReference<User> ref = new SoftReference<>(user);`
    - 메모리 부족할 때만 GC
    - 캐시에 주로 사용

    **3. Weak Reference (약한 참조)**

    - `WeakReference<User> ref = new WeakReference<>(user);`
    - 다음 GC 때 무조건 회수
    - WeakHashMap, 리플렉션 캐시에 사용

    **4. Phantom Reference (유령 참조)**

    - `PhantomReference<User> ref = ...;`
    - 객체에 접근 불가, GC 후 알림만 받음
    - 네이티브 리소스 정리용

### 5.2 우리 서버에서 WeakReference 54,008개

```
MAT에서 확인:
  java.lang.ref.WeakReference: 54,008개

이게 뭐냐:
  → 리플렉션 캐시가 WeakReference로 유지됨
  → 원래는 GC가 치워야 하는데
  → Strong Reference(Timer-0)가 잡고 있어서 GC 못함

정상적이라면:
  Timer-0 → TimerTask → 리플렉션 캐시(WeakRef) → ClassLoader
                                    ↑
                            Strong Ref가 끊기면 GC 가능

현재 상태:
  Timer-0(살아있음) → TimerTask(살아있음) → 리플렉션 캐시
                                    ↑
                          Timer-0가 잡고 있어서 GC 불가!
```

---

## 6. 메모리 누수 vs 메모리 릭

### 6.1 용어 정리

```
메모리 누수 (Memory Leak):
  → 더 이상 안 쓰는 객체인데 참조가 남아있어서 GC가 못 치우는 것
  → 시간이 지날수록 메모리 사용량 증가
  → 결국 OutOfMemoryError

메모리 릭과 메모리 누수는 같은 말이다. (Leak = 누수)
```

### 6.2 메모리 누수 패턴

!!! warning "흔한 메모리 누수 패턴"
    **1. static 컬렉션에 계속 추가**

    - `static List<User> users = new ArrayList<>();`
    - `users.add(user);` -- 계속 추가만 하고 제거 안 함

    **2. 리스너/콜백 등록 후 해제 안 함**

    - `eventBus.register(listener);` -- 등록
    - `eventBus.unregister(listener);` -- 해제 안 함!

    **3. 스레드가 종료 안 됨**

    - `Timer timer = new Timer(); timer.schedule(task, 0, 1000);`
    - `timer.cancel()` 안 함 → 스레드 영원히 살아있음
    - **우리 서버가 바로 이 케이스!**

    **4. Connection/Stream 닫지 않음**

    - `InputStream is = new FileInputStream(file);`
    - `is.close()` 안 함 → 리소스 누수

    **5. 캐시에 넣고 안 빼냄**

    - `Map<String, Object> cache = new HashMap<>();`
    - `cache.put(key, heavyObject);` -- 영원히 캐시에 남아있음

---

## 7. 우리 서버 GC Root 분석 종합

MAT Leak Suspects 분석 결과:

Problem Suspect 1: 13,883개 java.lang.Class 인스턴스가 60 MB (17.74%) 차지

참조 잡고 있는 GC Root들:

| GC Root | 참조 수 | 의미 |
|---------|---------|------|
| java.lang.Class (자기 자신) | 4,133 | 클래스 상호참조 |
| Log4jThread | 3,028 | 로깅 스레드 |
| TimerThread (Timer-0) | 2,332 | 1초 타이머 |
| whatap.agent.AsyncRunner | 325 | WhaTap APM |
| java.lang.Thread | 34 | 일반 스레드 |
| FastThreadLocalThread (Netty) | 20 | Netty 스레드 |
| TaskThread (Tomcat) | 8 | 요청 처리 |
| 기타 | 120 | - |

!!! danger "핵심"
    Timer-0가 2,332개 객체를 잡고 있다 → 이 스레드 하나가 전체 문제의 핵심 → interval=0으로 Timer-0 생성을 막으면 해결

---

## 8. 핵심 정리

!!! abstract "핵심 정리"
    **GC (Garbage Collection):**

    - 안 쓰는 객체를 자동으로 메모리에서 회수
    - Mark → Sweep (→ Compact) 순서
    - Stop-The-World 발생 (애플리케이션 잠시 멈춤)

    **GC Root:**

    - GC 탐색의 시작점
    - 스레드 지역변수, 활성 스레드, static 변수, JNI 참조 등
    - GC Root에서 도달 가능한 객체는 살아남음
    - 도달 불가능한 객체는 가비지 → 회수

    **Number of GC roots 5,863:**

    - 탐색 시작점 5,863개
    - 정상 범위 내
    - 하지만 그 중 Timer-0가 문제의 핵심

    **메모리 누수:**

    - 안 쓰는 객체인데 참조가 남아서 GC 못 하는 것
    - 살아있는 스레드가 참조 잡으면 연쇄적으로 보호
    - 시간이 지날수록 심해짐 → OOM 터짐

    **참조 강도:** Strong > Soft > Weak > Phantom

    - Strong: GC 안 됨
    - Weak: 다음 GC 때 회수 (BUT Strong이 잡으면 못 회수)

    **다음 장:** 힙 덤프와 hprof 포맷 -- "496MB 파일이 뭘 담고 있는지"
