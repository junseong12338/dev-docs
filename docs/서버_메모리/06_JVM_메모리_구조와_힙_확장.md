# 06. JVM 메모리 구조와 힙 확장 - Gamma

---

## 1. 핵심 개념 - "이게 뭐야?"

### 공장 비유로 문 연다

JVM의 메모리 구조? 큰 공장이라고 생각해봐.

!!! example "JVM 공장 비유"

    - **[작업장 - Heap]** 생산품(객체)을 만들고 쌓아두는 곳. 가장 넓고, 가장 바쁜 구역. GC 청소부가 여기서 쓰레기를 치움.
    - **[사무실 - Non-Heap]** 설계도(클래스 정보), 매뉴얼(상수) 등을 보관. 한번 넣으면 잘 안 바뀜.
    - **[창고 - Native Memory]** JVM 자체가 쓰는 공간. 스레드 관리, OS 연동 등 내부 운영용.

비유는 입구일 뿐이야. 본질로 가자.

### JVM 메모리의 본질

JVM이 OS로부터 받은 메모리는 크게 3가지 영역으로 나뉘어:

!!! note "JVM 메모리 전체 구조"

    **1. Heap (힙)** → new로 만든 모든 객체가 사는 곳. -Xms, -Xmx로 크기 제어. GC의 주 활동 무대. 가장 크고, 가장 많이 논의되는 영역.

    **2. Non-Heap (비힙)** → Metaspace: 클래스 메타데이터 (Java 8+) / Code Cache: JIT 컴파일된 네이티브 코드 / Compressed Class Space: 압축된 클래스 포인터

    **3. Native Memory (네이티브 메모리)** → Thread Stacks: 각 스레드의 스택 (-Xss로 제어) / Direct ByteBuffer: NIO에서 사용하는 OS 직접 메모리 / JVM 내부 구조체: GC 자체가 쓰는 메모리 등

    **top에서 보이는 RES = Heap + Non-Heap + Native Memory 전부 합친 것**

이 중에서 Heap이 제일 중요해. 왜? 우리가 만드는 모든 객체가 여기 사니까. 그리고 메모리 문제의 대부분이 여기서 발생하니까.

---

## 2. 동작 원리 - "어떻게 돌아가?"

### 2-1. Heap 상세 구조

힙은 다시 Young Generation과 Old Generation으로 나뉘어. 이게 왜 나뉘어져 있는지가 핵심이야.

!!! note "Heap 내부 구조"

    ```
    ┌──────────────────── Heap (-Xms ~ -Xmx) ────────────────────────┐
    │                                                                  │
    │  ┌──── Young Generation ────┐  ┌──── Old Generation ──────────┐ │
    │  │                          │  │                               │ │
    │  │  ┌──────────────────┐   │  │                               │ │
    │  │  │      Eden        │   │  │     Old (Tenured)             │ │
    │  │  │  (신생아실)       │   │  │     (양로원)                  │ │
    │  │  │  새 객체 탄생    │   │  │                               │ │
    │  │  └──────────────────┘   │  │     오래 살아남은 객체        │ │
    │  │  ┌────────┐ ┌────────┐  │  │     GC에서 계속 살아남아서    │ │
    │  │  │  S0    │ │  S1    │  │  │     여기로 승격된 객체들      │ │
    │  │  │(생존1) │ │(생존2) │  │  │                               │ │
    │  │  └────────┘ └────────┘  │  │                               │ │
    │  └──────────────────────────┘  └───────────────────────────────┘ │
    │  ◄── 보통 힙의 1/3 ──────►   ◄───── 보통 힙의 2/3 ──────────► │
    └──────────────────────────────────────────────────────────────────┘
    ```

    - **S0** = Survivor 0 (From)
    - **S1** = Survivor 1 (To)
    - 둘 중 하나는 항상 비어있어! (복사 알고리즘)

| 영역 | 역할 | 특징 |
|------|------|------|
| **Eden** | 새 객체가 처음 생기는 곳 | `new MyObject()`하면 여기에 할당 |
| **Survivor 0/1** | Eden에서 살아남은 객체가 오는 곳 | 둘이 번갈아가며 사용 |
| **Old** | 오래 살아남은 객체가 승격되는 곳 | Full GC의 대상 |

### 2-2. 객체의 일생: Eden에서 Old까지

!!! note "객체의 일생 (생로병사)"

    **[1] 탄생:** `new Object()` → Eden에 할당됨 → age = 0

    **[2] 첫 번째 생존 (Minor GC):** Eden이 꽉 참 → Minor GC 발동 → 살아있는 객체를 Survivor 0으로 복사 → Eden 전체를 비움 (죽은 객체 일괄 삭제) → age = 1

    **[3] 두 번째 생존 (다음 Minor GC):** Eden + Survivor 0에서 살아남은 객체를 Survivor 1로 복사 → Eden + Survivor 0 전체를 비움 → age = 2

    **[4] 계속 생존...:** S0 → S1 → S0 → S1... 핑퐁처럼 왔다갔다. 살아남을 때마다 age + 1

    **[5] 승격 (Promotion):** age가 임계값 도달 (기본 15, `-XX:MaxTenuringThreshold`) → Old Generation으로 승격! → 이제 Full GC 때만 검사 대상

    **[6] 사망:** 어딘가에서 참조가 끊김 → GC가 "이거 쓰레기"로 판정 → Minor GC(Young) 또는 Full GC(Old)에서 제거됨

좀 더 구체적으로 보자:

```
시점 1: Eden에 객체 A, B, C 생성
┌─────────────────────────────────────────────────┐
│ Eden: [A][B][C]     S0: []     S1: []    Old: []│
└─────────────────────────────────────────────────┘

시점 2: Minor GC. B는 죽음, A와 C는 살아남음
┌─────────────────────────────────────────────────┐
│ Eden: [비움]      S0: [A(1)][C(1)]  S1: []  Old: []│
└─────────────────────────────────────────────────┘

시점 3: Eden에 D, E 생성 후 또 Minor GC. D는 죽음
┌─────────────────────────────────────────────────┐
│ Eden: [비움]  S0: []  S1: [A(2)][C(2)][E(1)]  Old: []│
└─────────────────────────────────────────────────┘

시점 N: A의 age가 15 도달 → Old로 승격
┌─────────────────────────────────────────────────┐
│ Eden: [...]  S0: [...]  S1: [...]  Old: [A(15)]│
└─────────────────────────────────────────────────┘
```

### 2-3. Weak Generational Hypothesis - 왜 Young/Old로 나눴는가

이 질문이 핵심이야. 왜 귀찮게 Young과 Old를 나눠놨을까?

!!! note "Weak Generational Hypothesis (약한 세대 가설)"

    **관찰된 사실: "대부분의 객체는 생성되자마자 금방 죽는다"**

    ```
    객체 수
    │
    │████
    │████
    │████████
    │████████
    │████████████
    │████████████
    │████████████████
    │████████████████████
    │████████████████████████████
    │████████████████████████████████████████████
    └──────────────────────────────────────────── 생존 시간
     짧다                                         길다
    ```

    → 대다수의 객체는 아주 짧게 살고 죽는다 (왼쪽에 몰려있음). → 소수의 객체만 오래 산다 (오른쪽으로 갈수록 적음)

    **그래서 어떻게 했냐면:** 짧게 사는 객체 전용 구역 (Young) + 오래 사는 객체 전용 구역 (Old). Young은 자주 청소 (Minor GC) -- 빠름. Old는 가끔 청소 (Full GC) -- 느리지만 덜 자주.

    **이게 왜 효율적이냐면:** 전체 힙을 매번 청소하면 너무 오래 걸려. 어차피 대부분의 쓰레기는 Young에서 나오니까, Young만 자주 청소하면 대부분의 쓰레기를 빠르게 처리할 수 있어. Old에 있는 객체는 오래 살 확률이 높으니까 자주 검사할 필요 없고.

실제 예시로 보면:

```
HTTP 요청 하나 처리할 때 만들어지는 객체들:

Request 객체     → 요청 끝나면 죽음          → Young에서 정리
Response 객체    → 응답 보내면 죽음          → Young에서 정리
VO/DTO 객체      → 처리 끝나면 죽음          → Young에서 정리
임시 String들    → 연산 끝나면 죽음          → Young에서 정리

반면:
DB 커넥션 풀     → 앱 종료까지 살아있음      → Old로 승격
Spring Bean      → 앱 종료까지 살아있음      → Old로 승격
캐시 데이터      → TTL까지 살아있음          → Old로 승격
```

### 2-4. -Xms와 -Xmx의 관계

이제 05장에서 배운 JVM 옵션과 연결하자.

!!! note "-Xms와 -Xmx의 관계"

    **-Xms** = 시작 크기 (Initial Heap Size) → JVM 시작 시 OS한테 "이만큼 힙으로 쓸게" 하고 committed 하는 양

    **-Xmx** = 최대 크기 (Maximum Heap Size) → 힙이 절대 넘을 수 없는 벽. 이걸 넘으면 OutOfMemoryError

    **Case 1: -Xms = -Xmx (같은 값)** → 힙이 처음부터 고정 크기. 확장/축소 없음 → 예측 가능한 성능. **프로덕션 권장 설정**

    **Case 2: -Xms < -Xmx (다른 값) ← 우리 서버!** → 힙이 점진적으로 확장됨. 모니터링에서 "메모리가 올라간다" 현상의 원인.

    ```
    시작: [██████████████████████░░░░░░░░░░░░]
    확장: [██████████████████████████████░░░░]
    최대: [██████████████████████████████████]
          ◄──── -Xms=8GB ───►
          ◄────────────── -Xmx=12GB ────────►
    ```

    **Case 3: -Xms > -Xmx (잘못된 설정)** → JVM이 시작을 거부함. 에러 발생. "Initial heap size set to a larger value than the maximum heap"

### 2-5. 힙 확장 과정 상세

이게 이 챕터의 핵심 중 핵심이야. -Xms < -Xmx일 때 힙이 어떻게 확장되는지.

!!! note "힙 확장 과정 (Step by Step)"

    **[1] JVM 시작** → OS한테 -Xms(8GB)만큼 힙 메모리 committed. committed = 8GB, resident ≈ 일부 (아직 다 안 건드림)

    **[2] 서비스 운영 중** → 사용자 요청 처리하면서 객체 생성/삭제 반복. Eden 꽉 참 → Minor GC. 살아남는 객체 → Survivor → 반복 → Old로 승격

    **[3] JVM의 GC 성능 분석** → "GC 후에도 살아있는 객체가 많네" / "GC 빈도가 너무 잦아지고 있네" / "Eden이 너무 작아서 금방 차네" → JVM 판단: "힙을 늘려야겠다"

    **[4] 힙 확장 요청** → JVM이 OS한테 추가 메모리 요청. OS: "OK, 가상 주소 공간 추가 할당" (committed 증가). 예: 8GB → 9.5GB → 11GB → ... (점진적)

    **[5] 새 영역에 객체 할당** → 확장된 힙 공간에 새 객체 할당 시작. 새 가상 페이지에 첫 접근 → page fault. 물리 RAM 페이지 할당 → resident 증가

    **[6] 모니터링 수치 변화** → committed: 8GB → 11.26GB (힙 확장된 만큼). resident: 5GB → 8.4GB (실제 쓰인 만큼). 모니터링 %MEM: 34% → 55%. **"메모리가 올라가고 있어요!" ← 이건 정상 동작!**

    **[7] 최대 도달** → committed가 -Xmx(12GB)에 도달하면 더 이상 확장 불가. 이 상태에서 힙이 부족하면 → OutOfMemoryError

### 2-6. 왜 -Xms = -Xmx로 맞춰야 하는가

우리 서버는 -Xms=8GB, -Xmx=12GB로 다르게 설정돼 있어. 이게 왜 문제가 될 수 있는지 보자.

!!! warning "-Xms ≠ -Xmx 일 때 발생하는 문제들"

    **문제 1: 확장 시 GC 오버헤드** -- 힙을 확장하려면 JVM이 GC를 돌려서 "진짜 더 필요한가" 확인해. 이 과정에서 GC가 불필요하게 발생할 수 있어. → GC = Stop The World = 앱 일시 정지 = 사용자 응답 지연

    **문제 2: OS 재요청 비용** -- 힙 확장 = OS한테 추가 메모리 요청. mmap() 시스템 콜 → 가상 주소 공간 확보 → 페이지 테이블 업데이트. 빈번하게 일어나면 오버헤드.

    **문제 3: 예측 불가능한 성능** -- "지금 힙이 8GB인지 10GB인지 12GB인지" 모름. 같은 요청인데 힙 크기에 따라 GC 동작이 달라짐. → 응답 시간이 들쭉날쭉.

    **문제 4: "점점 올라가는" 모니터링 수치** -- 힙 확장 → committed 증가 → resident 증가 → 모니터링 % 상승. "메모리가 계속 올라가고 있어요! 누수 아니에요?" → 아니야, 힙 확장이야. 근데 구분이 어렵지. → -Xms = -Xmx면 이 혼란 자체가 없어짐.

    **해결: -Xms = -Xmx** → `-Xms12288m -Xmx12288m` (둘 다 12GB). 시작부터 전체 힙 확보. 확장 없음 → GC 오버헤드 없음. 모니터링 수치 안정적. **프로덕션 서버의 모범 사례.**

    **트레이드오프:** 처음부터 12GB committed → 안 쓰는 만큼 "예약만 한" 상태. 다른 프로세스가 그만큼 못 씀. 근데 프로덕션 서버는 보통 JVM 하나만 도니까 괜찮음.

### 2-7. Metaspace (Java 8+)

05장에서 `-XX:MaxPermSize`가 Java 8에서 무시된다고 했지? 그 이유가 이거야.

!!! note "PermGen → Metaspace 변천사"

    ```
    Java 7 이하:
    ┌─────── Heap ───────┐ ┌── PermGen ──┐
    │ Young │    Old      │ │ 클래스 정보 │  ← 힙 안에 있었음
    └────────────────────┘ │ 상수 풀     │  ← 크기 고정 (-XX:MaxPermSize)
                           │ 메서드 정보 │  ← 꽉 차면 OOM
                           └─────────────┘

    Java 8 이상:
    ┌─────── Heap ───────┐ ┌── Metaspace ──┐
    │ Young │    Old      │ │ 클래스 정보    │  ← 힙 밖, Native Memory!
    └────────────────────┘ │ 메서드 정보    │  ← 기본 무제한 확장
                           │ (상수 풀은     │  ← 제한하려면
                           │  힙으로 이동!) │    -XX:MaxMetaspaceSize
                           └────────────────┘
    ```

    **바뀐 이유:**

    1. PermGen 크기를 얼마로 잡을지 예측이 어려웠음
    2. PermGen이 꽉 차면 OOM → 웹앱 재배포 시 클래스 로더 누수로 자주 발생
    3. 힙 밖(Native Memory)으로 빼면 OS가 알아서 관리
    4. 필요한 만큼 자동으로 커짐

**Metaspace 무제한 확장의 위험:**

!!! danger "Metaspace를 제한 없이 두면?"

    **클래스 로더 누수(ClassLoader Leak) 발생 시:** 웹앱 재배포할 때마다 클래스가 새로 로드됨 → 옛날 클래스가 안 지워지고 누적 → Metaspace가 끝없이 커짐 → 결국 OS 메모리 전체를 먹어서 서버 다운

    **권장:** `-XX:MaxMetaspaceSize=512m` (또는 적절한 크기). 제한을 걸어놓으면 누수 시 OOM으로 빠르게 발견 가능. 제한 없으면 서서히 죽어서 원인 파악이 어려움.

### 2-8. -XX:MaxPermSize가 Java 8에서 무시되는 이유

이제 확실히 이해될 거야.

```
Java 8에서 PermGen이 사라졌으니까.

-XX:MaxPermSize=4096m
→ PermGen이 없는데 PermGen 크기를 설정?
→ "뭘 설정하라는 건데?"
→ JVM: "이 옵션 무시할게. 경고만 하나 찍을게."
→ 로그: "MaxPermSize=4096m; support was removed in 8.0"

우리 서버에 남아있는 이 옵션은 Java 7→8 업그레이드 때 안 지운 잔재야.
동작에는 영향 없지만, 알고는 있어야 해.
```

### 2-9. 실제 우리 서버 사례 연결

!!! abstract "우리 LMS 서버 실제 수치와 이 챕터의 연결"

    **설정:** -Xms8192m -Xmx12288m / **서버 RAM:** 약 15.3GB (가용)

    **관측 수치:** committed: 약 11.26GB / resident (RSS): 약 8.4GB / 모니터링 %MEM: 약 55%

    **이게 뜻하는 것:**

    1. -Xms=8GB에서 시작
    2. JVM이 힙을 확장 (GC 성능 분석 후)
    3. committed ≈ 11.26GB (힙 + Non-Heap + Native) → 아직 -Xmx=12GB까지 여유 있음
    4. resident ≈ 8.4GB (실제 물리 RAM에 올라간 양) → committed 중에서 실제 건드린 부분
    5. %MEM = 8.4GB / 15.3GB ≈ 55% → 모니터링이 "55%"라고 보여주는 이유
    6. **이건 정상이야!** 힙 확장 + 정상 사용 = 이 정도 수치

    **만약 -Xms = -Xmx = 12GB로 설정했다면:** 시작부터 committed ≈ 12GB + Non-Heap. resident는 시간이 지나면서 비슷한 수준. 하지만 "점점 올라가는" 혼란은 없었을 것.

---

## 3. 코드/명령어로 보자

### 3-1. JVM 힙 상태 확인 (jstat)

```bash
# jstat: JVM 통계 모니터링 도구
# -gc: GC 관련 통계
# $(pgrep -f 'catalina'): 톰캣 JVM의 PID
# 1000: 1초(1000ms)마다 출력
# 5: 5번만 출력
jstat -gc $(pgrep -f 'catalina') 1000 5
```

출력 예시:
```
 S0C    S1C    S0U    S1U      EC       EU        OC         OU       MC     MU
34048  34048   0.0   32012  272384   45123    8036352   5765123   125952  121234
```

| 컬럼 | 의미 | 설명 |
|------|------|------|
| S0C | Survivor 0 Capacity | S0 전체 크기 (KB) |
| S1C | Survivor 1 Capacity | S1 전체 크기 (KB) |
| S0U | Survivor 0 Used | S0 사용량 (KB) |
| S1U | Survivor 1 Used | S1 사용량 (KB) |
| EC | Eden Capacity | Eden 전체 크기 (KB) |
| EU | Eden Used | Eden 사용량 (KB) |
| OC | Old Capacity | Old 전체 크기 (KB) |
| OU | Old Used | Old 사용량 (KB) |
| MC | Metaspace Capacity | Metaspace 전체 크기 (KB) |
| MU | Metaspace Used | Metaspace 사용량 (KB) |

!!! tip "이 숫자들이 뜻하는 것"

    **힙 전체 committed** = S0C + S1C + EC + OC = 34048 + 34048 + 272384 + 8036352 = 8,376,832 KB ≈ **약 8GB**

    **힙 전체 used** = S0U + S1U + EU + OU = 0 + 32012 + 45123 + 5765123 = 5,842,258 KB ≈ **약 5.6GB**

    **힙 사용률** = used / committed ≈ 5.6GB / 8GB ≈ **70%**

    이건 JVM 내부에서 보는 "진짜 객체가 차지하는 양"이야. OS가 보는 RSS(8.4GB)와는 다른 숫자!

### 3-2. 힙 사용률 추이 확인

```bash
# -gcutil: GC 통계를 퍼센트(%)로 보여줌
# 10000: 10초마다
# 100: 100번 (약 16분간)
jstat -gcutil $(pgrep -f 'catalina') 10000 100
```

출력 예시:
```
  S0     S1     E      O      M     CCS    YGC     YGCT    FGC    FGCT     GCT
  0.00  94.12  16.57  71.73  96.25  93.47    523    8.234     3    1.456   9.690
```

| 컬럼 | 의미 | 위의 값 해석 |
|------|------|-------------|
| S0/S1 | Survivor 사용률(%) | S1만 94% 사용 중 (정상, 하나만 씀) |
| E | Eden 사용률(%) | 16.57% → Eden에 여유 있음 |
| O | Old 사용률(%) | 71.73% → Old가 꽤 찬 상태 |
| M | Metaspace 사용률(%) | 96.25% → 거의 다 참 |
| YGC | Young GC 횟수 | 523번 Minor GC 발생 |
| FGC | Full GC 횟수 | 3번 Full GC 발생 |
| GCT | 전체 GC 시간(초) | 총 9.69초 (JVM 전체 가동 중) |

### 3-3. JVM 메모리 영역별 상세 확인

```bash
# jmap -heap: JVM 힙 설정과 사용량 상세
jmap -heap $(pgrep -f 'catalina')
```

출력 예시:
```
Heap Configuration:
   MinHeapFreeRatio         = 0
   MaxHeapFreeRatio         = 100
   MaxHeapSize              = 12884901888 (12288.0MB)    ← -Xmx
   NewSize                  = ...
   MaxNewSize               = ...
   OldSize                  = ...

Heap Usage:
Eden Space:
   capacity = 278921216 (266.0MB)
   used     = 46123456 (43.99MB)
   free     = 232797760 (222.01MB)
   16.54% used

From Space (S0):
   capacity = 34865152 (33.25MB)
   used     = 0 (0.0MB)
   0.0% used

To Space (S1):
   capacity = 34865152 (33.25MB)
   used     = 32780000 (31.26MB)
   94.02% used

PS Old Generation:
   capacity = 8229175296 (7848.0MB)
   used     = 5903485952 (5630.42MB)
   free     = 2325689344 (2217.58MB)
   71.74% used
```

---

## 4. 주의사항 / 함정

!!! danger "함정 1: \"Old가 80% 차면 위험!\"이라고 무조건 판단"

    **틀린 판단:** "Old 사용률 80%! 곧 OOM 터지겠네!"

    **맞는 판단:** Old 사용률만 보면 안 돼. Full GC 후의 Old 사용률을 봐야 해. Full GC 돌고 나서도 80%면? → 그건 진짜 위험. Full GC 돌고 나서 30%면? → 정상. 다음 Full GC까지 차오르는 중일 뿐.

    **핵심은 "GC 후에도 줄어들지 않는 양"이야. 이게 계속 커지면 그때가 메모리 누수.**

!!! danger "함정 2: Metaspace를 무제한으로 방치"

    **위험한 설정:** -XX:MaxMetaspaceSize 미설정 (기본 = 무제한)

    **안전한 설정:** `-XX:MaxMetaspaceSize=512m` (또는 적절한 크기)

    **이유:** 클래스 로더 누수가 발생하면 Metaspace가 끝없이 커져. 제한이 없으면 서버 전체 RAM을 먹을 때까지 조용히 자라다가 갑자기 서버가 죽어. 원인 파악도 어려워. 제한을 걸면 OOM으로 빠르게 알 수 있어.

!!! danger "함정 3: \"RSS와 힙 사용량이 달라!\" → 누수 의심"

    **틀린 반응:** "jstat에서 힙 5.6GB인데 RSS는 8.4GB야! 2.8GB가 어디 갔어? 누수다!"

    **맞는 이해:** RSS = Heap used + Heap의 빈 공간도 포함 + Non-Heap + Native Memory

    **RSS 8.4GB 분해:**

    | 구성 요소 | 크기 |
    |-----------|------|
    | Heap committed | ~8GB (이 안에 used 5.6GB) |
    | Metaspace | ~120MB |
    | Code Cache | ~50MB |
    | Thread Stacks | ~200MB (200개 * 1MB) |
    | APM Agent | ~100MB |
    | Direct ByteBuffer, 기타 | 나머지 |
    | **합계** | **약 8.4GB** |

    힙 committed 전체(8GB)가 RSS에 포함돼. 힙 안에서 used가 5.6GB이든 3GB이든, OS 입장에서는 힙 전체가 물리 RAM에 올라가 있는 거야.

!!! danger "함정 4: Young Generation 크기를 함부로 건드림"

    **위험한 행동:** "Minor GC가 자주 발생하니까 Young을 엄청 키우자!" `-XX:NewRatio=1` (Young:Old = 1:1)

    **신중한 접근:** Young을 키우면 Minor GC 빈도는 줄어들지만:

    - Minor GC 한 번의 시간이 길어짐 (더 많은 객체 스캔)
    - Old 공간이 줄어들어서 Full GC가 더 자주 발생할 수 있음
    - Full GC > Minor GC (훨씬 더 비쌈)

    → GC 튜닝은 측정 → 분석 → 변경 → 재측정 사이클이야. 감으로 하면 더 나빠질 수 있어.

!!! danger "함정 5: 힙 확장을 누수로 오해"

    **잘못된 판단 과정:** 1. 서비스 시작 직후: 메모리 34% → 2. 1시간 후: 메모리 45% → 3. 3시간 후: 메모리 55% → 4. "계속 올라가니까 누수다!"

    **올바른 판단 과정:**

    1. -Xms(8GB) < -Xmx(12GB)이니까 힙 확장이 먼저 의심
    2. jstat -gcutil로 GC 후 Old 사용률 확인
    3. Full GC 후에도 Old가 계속 커지면 → 그때 누수 의심
    4. Full GC 후 Old가 안정적이면 → 힙 확장일 뿐, 정상
    5. 확인하려면 jmap으로 힙덤프 떠서 분석

---

## 5. 정리

### JVM 메모리 전체 구조 요약

!!! abstract "JVM 메모리 최종 정리"

    ```
    ┌── Heap (힙) ──────────────────────────────────┐
    │  Young: Eden + S0 + S1  (새 객체, 빠른 GC)    │  -Xms, -Xmx로 제어
    │  Old: Tenured           (오래 산 객체, Full GC)│
    └────────────────────────────────────────────────┘

    ┌── Non-Heap ───────────────────────────────────┐
    │  Metaspace (Java 8+)    클래스 메타데이터      │  MaxMetaspaceSize
    │  Code Cache             JIT 컴파일 코드        │
    └────────────────────────────────────────────────┘

    ┌── Native Memory ──────────────────────────────┐
    │  Thread Stacks          각 스레드 스택         │  -Xss로 제어
    │  Direct ByteBuffer      NIO 직접 메모리        │
    │  JVM 내부               GC, JIT 등 내부 구조   │
    └────────────────────────────────────────────────┘

    RSS = Heap + Non-Heap + Native Memory (전부 합친 것)
    ```

### 핵심 요약 표

| 개념 | 설명 | 제어 옵션 |
|------|------|-----------|
| **Eden** | 새 객체 탄생 장소 | JVM 자동 조절 (-XX:NewRatio) |
| **Survivor** | 살아남은 객체 대기소 | JVM 자동 조절 |
| **Old** | 오래 산 객체 거주지 | 힙 - Young = Old |
| **-Xms** | 힙 시작 크기 | committed 초기값 |
| **-Xmx** | 힙 최대 크기 | committed 상한선 |
| **Metaspace** | 클래스 정보 저장 (Native) | -XX:MaxMetaspaceSize |
| **힙 확장** | -Xms에서 -Xmx까지 자동 성장 | -Xms = -Xmx로 방지 |

### 우리 서버 수치 최종 해석

| 수치 | 값 | 이게 뭔지 |
|------|-----|-----------|
| -Xms | 8GB | 힙 시작 크기 |
| -Xmx | 12GB | 힙 최대 크기 |
| committed | ~11.26GB | 힙 + Non-Heap + Native 전체 예약량 |
| resident (RSS) | ~8.4GB | 실제 물리 RAM에 올라간 양 |
| %MEM | ~55% | RSS / 전체 RAM |
| 상태 | **정상** | 힙 확장 + 정상 사용의 결과 |

### 한 줄 정리

> **JVM 힙은 Young(짧게 살다 죽는 객체)과 Old(오래 사는 객체)로 나뉘어 있고, -Xms < -Xmx면 힙이 자동 확장되면서 모니터링 수치가 올라간다. 이건 누수가 아니라 JVM의 정상 동작이다.**

---

### 확인 문제 (5문제)

> 다음 문제를 풀어봐. 답 못 하면 위에서 다시 읽어.

**Q1.** Weak Generational Hypothesis가 뭔지 한 문장으로 설명하고, 이 가설 때문에 JVM 힙이 어떻게 구성됐는지 말해봐.

**Q2.** 새 객체가 생성되어 Old Generation에 도달하기까지의 과정을 순서대로 나열해봐. (최소 4단계)

**Q3.** 우리 서버 설정이 `-Xms8192m -Xmx12288m`이다. 프로덕션 환경에서 이 두 값을 같게 맞추는 것이 권장되는 이유를 3가지 말해봐.

**Q4.** Java 8에서 `-XX:MaxPermSize=4096m` 옵션이 무시되는 이유를 설명하고, 대신 뭘 써야 하는지 말해봐.

**Q5.** jstat에서 힙 used가 5.6GB이고, top에서 RSS가 8.4GB다. 이 차이(2.8GB)는 뭘 뜻하는가?

??? success "정답 보기"
    **A1.** "대부분의 객체는 생성되자마자 금방 죽는다"는 경험적 관찰. 이 가설에 따라 JVM 힙을 Young Generation(짧게 사는 객체 전용, 자주 GC)과 Old Generation(오래 사는 객체 전용, 가끔 GC)으로 나눠서, 전체 힙을 매번 청소하지 않고 Young만 자주 청소해도 대부분의 쓰레기를 효율적으로 처리할 수 있게 했다.

    **A2.** (1) Eden에서 `new`로 생성됨 (age=0) (2) Minor GC 발생 시 살아남으면 Survivor 영역으로 복사 (age=1) (3) 이후 Minor GC마다 Survivor 0과 1 사이를 핑퐁하며 이동, 살아남을 때마다 age 증가 (4) age가 임계값(기본 15)에 도달하면 Old Generation으로 승격(Promotion)

    **A3.** (1) 힙 확장 시 GC를 트리거해서 "진짜 더 필요한가" 확인하는 오버헤드가 발생하는데, 같으면 확장 자체가 없으니 이 오버헤드가 없다. (2) 힙 확장은 OS에게 추가 메모리를 요청하는 시스템 콜 비용이 드는데, 같으면 시작 시 한 번만 요청하면 된다. (3) 모니터링 수치가 시작부터 안정적이어서, 힙 확장으로 인한 "메모리가 점점 올라간다" 현상을 누수로 오해하는 혼란을 방지할 수 있다.

    **A4.** Java 8부터 PermGen(Permanent Generation)이 제거되고 Metaspace로 대체됐기 때문이다. MaxPermSize는 PermGen의 크기를 설정하는 옵션인데, 대상 자체가 없어졌으니 무시된다. JVM은 "support was removed in 8.0" 경고만 출력하고 넘어간다. Metaspace 크기를 제한하려면 `-XX:MaxMetaspaceSize=<크기>`를 사용해야 한다.

    **A5.** 이 차이는 힙의 빈 공간(committed되었지만 아직 객체가 안 들어간 영역) + Non-Heap(Metaspace, Code Cache 등) + Native Memory(Thread Stacks, APM Agent, Direct ByteBuffer 등)를 합친 것이다. jstat의 used는 힙 안에서 실제 살아있는 객체가 차지하는 양이고, RSS는 JVM 프로세스가 물리 RAM에 올려놓은 전체 양이기 때문에 항상 RSS > 힙 used이다. 이건 정상적인 차이이지 메모리 누수가 아니다.
