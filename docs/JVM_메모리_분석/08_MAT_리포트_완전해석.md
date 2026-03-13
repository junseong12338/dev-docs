# 08. MAT 리포트 완전 해석

**이 장의 목표**: 13개 항목을 종합해서 "리포트 보고 뭘 해야 하는지" 판단할 수 있다

---

## 1. 분석 프로세스

``` mermaid
graph TB
    S1["<b>Step 1: System Overview 확인</b><br/>전체 상태 파악<br/>정상/비정상 빠르게 판단"]
    S2["<b>Step 2: Leak Suspects 확인</b><br/>MAT이 자동 탐지한<br/>누수 의심 지점"]
    S3["<b>Step 3: Dominator Tree 확인</b><br/>메모리 점유 상위 객체<br/>누가 메모리 많이 먹나"]
    S4["<b>Step 4: GC Root 추적</b><br/>문제 객체를 잡고 있는 GC Root 찾기<br/>누가 이 객체를 안 놓아주는 거야?"]
    S5["<b>Step 5: 원인 파악 → 코드 추적 → 해결</b><br/>GC Root를 따라 실제 코드 위치 확인<br/>수정 방안 도출"]
    S1 --> S2 --> S3 --> S4 --> S5
```

---

## 2. Step 1: System Overview 읽기

### 2.1 빨간 신호 찾기

```
우리 서버 System Overview:

  Used heap dump           323.4 MB      ← 양은 적음, 내용물이 문제
  Number of objects        5,231,251     ← 정상
  Number of classes        27,688        ← 약간 많음 (중복?)
  Number of class loaders  4,574         ← 비정상! (정상: 10~50)
  Number of GC roots       5,863         ← 정상

즉시 알 수 있는 것:
  ClassLoader 4,574개 → 뭔가 심각하게 잘못됨
  → "왜 ClassLoader가 이렇게 많지?" 가 첫 번째 질문
```

### 2.2 정상 범위 기준표

| 항목 | 정상 범위 | 경고 | 위험 |
|------|----------|------|------|
| Used heap / Xmx | 30~70% | 70~85% | 85%+ |
| Objects | 규모 따라 다름 | - | - |
| Classes | 10K~20K | 20K~30K | 30K+ |
| ClassLoaders | 10~50 | 50~500 | 500+ |
| GC roots | 2K~10K | - | - |

!!! danger "우리 서버"
    - Used/Xmx: 323MB/12GB = 2.6% → 정상 (너무 적어서 이상)
    - Classes: 27,688 → 경고 수준
    - ClassLoaders: 4,574 → **위험!!! (정상의 100배)**

---

## 3. Step 2: Leak Suspects 읽기

### 3.1 MAT이 찾은 문제

```
Problem Suspect 1:
  13,883 instances of "java.lang.Class"
  loaded by "<system class loader>"
  occupy 60,136,280 (17.74%) bytes

해석:
  java.lang.Class 객체 13,883개가
  힙의 17.74% (약 60 MB)를 차지하고 있다

  java.lang.Class = 클래스의 메타데이터를 힙에서 참조하는 객체
  13,883개 = 로드된 클래스마다 1개씩 존재
  → 클래스 27,688개 중 약 절반이 Leak Suspect
```

### 3.2 Leak Suspects 해석법

```
MAT Leak Suspects가 말해주는 것:

1. "이 객체(들)가 메모리의 큰 비중을 차지한다"
   → 반드시 누수는 아닐 수 있음
   → 정상적으로 많이 쓰는 것일 수도 있음

2. "이 비중이 비정상적으로 크다"
   → 17.74%가 Class 객체? 일반적으로 5% 미만이어야 함
   → 비정상

3. 판단 기준:
   → 시간이 지나면서 커지는가? → 누수
   → 항상 일정한가? → 정상적 사용
   → 재기동하면 줄었다가 다시 커지는가? → 누수 확실
```

---

## 4. Step 3: Dominator Tree 읽기

### 4.1 Dominator Tree란

```
Dominator Tree (도미네이터 트리):
  "이 객체가 GC되면 얼마나 메모리가 해제되는가"를
  Retained Heap 기준으로 정렬한 트리

= 메모리 점유 Top N
= "누가 메모리를 가장 많이 먹고 있나"
```

### 4.2 우리 서버 Dominator Tree

```
순위  객체                              Retained   비율
──────────────────────────────────────────────────────────
 1   RefreshableSqlSessionFactoryBean   18.5 MB    5.45%
 2   RefreshableSqlSessionFactoryBean   16.7 MB    4.92%
 3   ParallelWebappClassLoader          12.4 MB    3.65%
 4   SynchronizedStack (Tomcat)         12.3 MB    3.62%
 5   ThreadGroupContext                 10.8 MB    3.18%
 6   com.exem.jspd.b.c (EXEM APM)       9.4 MB    2.77%
 7   Cache (Tomcat)                      7.8 MB    2.29%
 8   RequestMappingHandlerMapping        7.6 MB    2.23%
 9   RingBuffer (Log4j2)                 7.3 MB    2.16%
10   com.exem.jspd.b.p (EXEM APM)       6.4 MB    1.89%

읽는 법:
  #1, #2: 같은 클래스가 2개 → Bean 중복 생성! (정상이면 1개)
  #3: WebApp ClassLoader가 2개 → 이전 배포 잔재
  #6, #10: APM이 메모리 상위에 → 모니터링 도구가 메모리를 많이 먹음
```

### 4.3 비정상 판단

```
RefreshableSqlSessionFactoryBean이 2개인 이유:

인스턴스 #1: DataSource = BasicDataSource           (18.5 MB)
인스턴스 #2: DataSource = Log4jdbcProxyDataSource    (16.7 MB)

→ Root Context와 Servlet Context에서 각각 1번씩 생성됨
→ Spring Context 중복 로드 문제
→ 35.2 MB 중 절반(16.7 MB)은 낭비

정상: SqlSessionFactoryBean 1개, 약 18 MB
현재: 2개, 35.2 MB → 약 17 MB 낭비
```

---

## 5. Step 4: GC Root 추적

### 5.1 "Path to GC Roots" 사용법

```
MAT에서 의심 객체 우클릭
→ "Path to GC Roots"
→ "exclude weak references" (약한 참조 제외)

그러면 이 객체를 살려두는 Strong Reference 체인이 나온다:

GC Root: java.util.TimerThread (Timer-0)
    ↓ (referent)
java.util.TimerTask$1
    ↓ (val$this)
RefreshableSqlSessionFactoryBean
    ↓ (mapperLocations)
Resource[126개]
    ↓ (리플렉션 캐시)
DelegatingClassLoader (4,257개)

해석:
  Timer-0 스레드가 살아있어서
  → TimerTask를 잡고 있고
  → TimerTask가 Bean을 잡고 있고
  → Bean이 리소스를 잡고 있고
  → 리소스 체크 시 리플렉션이 ClassLoader를 생성
  → 전부 GC 불가
```

### 5.2 GC Root 추적의 핵심

!!! question "GC Root 추적 핵심 질문"
    **Q1: "이 객체를 누가 잡고 있어?"** → Path to GC Roots로 확인

    **Q2: "그 GC Root는 왜 살아있어?"** → 스레드면: 왜 종료 안 됐는지 확인 / static이면: 왜 해제 안 했는지 확인

    **Q3: "이 참조를 끊으면 얼마나 해제돼?"** → Retained Heap 확인

    **Q4: "코드 어디서 이 참조가 생긴 거야?"** → 클래스명 → 소스코드 추적

---

## 6. Step 5: 원인 → 코드 → 해결

### 6.1 우리 서버 종합 분석

!!! danger "분석 결과 종합"
    **문제 1: ClassLoader 4,574개 (정상의 100배)**

    - 원인: RefreshableSqlSessionFactoryBean interval=1000
    - 코드: context-sqlMap.xml:14
    - 해결: interval=0
    - 효과: DelegatingClassLoader 생성 중단

    **문제 2: Bean 중복 생성 (35.2 MB)**

    - 원인: Spring Context 중복 로드
    - 코드: context-common.xml component-scan 범위
    - 해결: 스캔 범위 분리 (Root vs Servlet)
    - 효과: 약 17 MB 절약

    **문제 3: APM 2개 동시 실행 (~32 MB)**

    - 원인: EXEM + WhaTap 동시 로드
    - 코드: JVM 시작 옵션 -javaagent 2개
    - 해결: 1개로 단일화
    - 효과: 약 15 MB 절약 + 충돌 방지

    **문제 4: WebApp ClassLoader 2개 (17.3 MB)**

    - 원인: Tomcat Hot Deploy 잔재
    - 해결: 서버 재기동 (정상 동작)

    **총 낭비:** 약 52 MB (힙의 16%) / **핵심 조치:** interval=0 (즉시, 위험도 낮음)

### 6.2 조치 우선순위

```
즉시 (1순위): interval=0 설정
  → context-sqlMap.xml 한 줄 수정
  → 개발서버 테스트 → 운영 반영
  → 메모리 누수 근본 해결

중기 (2순위): APM 단일화 검토
  → 대표님/인프라팀 결정 필요
  → EXEM or WhaTap 택 1

장기 (3순위): Spring Context 중복 로드 해결
  → component-scan 범위 조정
  → 영향 범위 크고 테스트 많이 필요
```

---

## 7. 실전: 리포트를 처음 받았을 때 체크리스트

!!! example "MAT 리포트 분석 체크리스트"
    - [ ] **1. Used heap / Xmx 비율 확인** -- 70% 이상이면 메모리 부족 의심
    - [ ] **2. ClassLoader 수 확인** -- 50개 이상이면 ClassLoader 누수 의심
    - [ ] **3. Leak Suspects 확인** -- MAT이 찾은 의심 지점 리뷰
    - [ ] **4. Dominator Tree Top 10 확인** -- 동일 클래스 중복 인스턴스 있는지, 비정상적으로 큰 객체 있는지
    - [ ] **5. Histogram에서 이상 클래스 확인** -- 객체 수가 비정상적으로 많은 클래스, char[]/String이 최상위는 정상
    - [ ] **6. GC Root 추적** -- 문제 객체의 참조 체인 확인, 어떤 스레드/static이 잡고 있는지
    - [ ] **7. 코드 추적** -- GC Root → 클래스명 → 소스코드 위치, 왜 참조가 끊기지 않는지 확인
    - [ ] **8. 해결 방안 도출** -- 참조 끊기, 리소스 해제, 설정 변경 등, 위험도와 영향 범위 평가

---

## 8. 핵심 정리

!!! abstract "핵심 정리"
    **MAT 분석 5단계:**

    1. System Overview → 빨간 신호 찾기
    2. Leak Suspects → 자동 탐지 결과 확인
    3. Dominator Tree → 메모리 점유 Top N
    4. GC Root 추적 → 누가 잡고 있는지
    5. 코드 추적 → 원인 → 해결

    **우리 서버 분석 결과:**

    - 핵심 문제: interval=1000 (1초마다 파일 체크)
    - 증상: ClassLoader 4,574개 누적
    - 해결: interval=0 (한 줄 수정)

    **13개 항목 중 핵심 지표:**

    - ClassLoader 수 (비정상이면 즉시 의심)
    - Used heap / Xmx 비율 (메모리 여유 판단)
    - Compressed OOP (true여야 메모리 효율적)
