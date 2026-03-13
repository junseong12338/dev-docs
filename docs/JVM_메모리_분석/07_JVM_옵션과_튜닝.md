# 07. JVM 옵션과 튜닝

**이 장의 목표**: "Identifier size: 64-bit", "Compressed object pointers: true" 등 나머지 항목 이해

---

## 1. Identifier Size: 64-bit

### 1.1 Identifier란

```
Identifier = 객체의 메모리 주소(포인터)를 저장하는 크기

32-bit JVM: 주소를 4 byte로 표현
  → 최대 표현 가능: 2^32 = 약 4GB
  → 메모리 4GB까지만 사용 가능

64-bit JVM: 주소를 8 byte로 표현
  → 최대 표현 가능: 2^64 = 사실상 무한
  → 메모리 제한 거의 없음
```

### 1.2 왜 중요한가

| 구분 | 32-bit JVM | 64-bit JVM |
|------|-----------|-----------|
| 메모리 | 최대 4GB | 사실상 무제한 |
| 포인터 크기 | 4 byte | 8 byte |
| 객체 헤더 | 8 byte (Mark Word 4 + Class Pointer 4) | 16 byte (Mark Word 8 + Class Pointer 8) |
| 메모리 효율 | 좋음 | 32-bit 대비 30~50% 더 사용 |
| 단점 | 4GB 제한이 치명적 | 메모리 낭비 있음 |

!!! info "우리 서버: 64-bit"
    - 힙 최대 12GB 설정 → 64-bit 필수
    - 8 byte 포인터 사용 → 메모리 낭비 있음
    - 이걸 해결하는 게 Compressed OOP

---

## 2. Compressed Object Pointers (OOP): true

### 2.1 문제: 64-bit의 메모리 낭비

```
64-bit JVM에서 객체 참조(포인터)가 8 byte

예: User 객체에 String name 필드가 있으면
  name 참조 = 8 byte (64-bit)

32-bit였으면:
  name 참조 = 4 byte

객체가 523만 개 있고, 객체당 참조가 평균 5개라면:
  64-bit: 523만 x 5 x 8 byte = 209 MB (참조만)
  32-bit: 523만 x 5 x 4 byte = 104 MB (참조만)

→ 64-bit는 참조만으로 105 MB 더 쓴다!
```

### 2.2 해결: Compressed OOP

!!! tip "Compressed OOP (압축된 객체 포인터)"
    **아이디어:** 64-bit JVM인데 포인터를 4 byte로 쓸 수 있게 하자 → 32-bit의 메모리 효율 + 64-bit의 대용량 = 최고

    **원리:**

    - JVM은 객체를 8 byte 단위(정렬)로 배치한다
    - 주소의 하위 3 bit는 항상 000
    - 이 3 bit를 저장 안 해도 됨
    - 35-bit 주소를 32-bit에 저장 가능
    - 2^35 = 32 GB까지 표현 가능!

    **조건:** 힙 크기가 32 GB 이하면 자동 활성화 / 32 GB 초과하면 비활성화 (8 byte 포인터 사용)

    **우리 서버:** 힙 최대: 12 GB (-Xmx12288m). 12 GB < 32 GB → Compressed OOP 자동 활성화 → "Compressed object pointers: true"

    **효과:**

    - 포인터: 8 byte → 4 byte (50% 절약)
    - 객체 헤더: 16 byte → 12 byte (25% 절약)
    - 전체 힙: 약 30~40% 메모리 절약

### 2.3 Compressed OOP 활성화 여부 확인

```
MAT System Overview에서:
  Compressed object pointers: true
  → 활성화됨!

확인 방법 (커맨드):
  java -XX:+PrintFlagsFinal -version 2>&1 | grep UseCompressedOops

JVM 옵션으로 제어:
  -XX:+UseCompressedOops   (활성화, 기본값)
  -XX:-UseCompressedOops   (비활성화)
```

### 2.4 함정: 힙을 32GB 이상으로 설정하면

!!! warning "32GB 함정"
    **-Xmx31g (31 GB):** Compressed OOP ON → 포인터 4 byte. 실제 사용 가능: 31 GB

    **-Xmx32g (32 GB):** Compressed OOP OFF → 포인터 8 byte. 포인터 크기 2배 → 실질적으로 사용 가능한 양 감소 → 31GB보다 실제 객체 저장량이 적을 수 있음!

    **결론:** 힙을 32GB로 설정하면 오히려 손해. 31GB 이하 또는 48GB 이상으로 설정해야 효율적 → "32GB 힙의 역설"

    **우리 서버:** 12GB → 이 함정에 해당 없음

---

## 3. JVM 주요 옵션 정리

### 3.1 우리 서버의 JVM 옵션

```
-Xms8192m                          힙 초기 크기: 8 GB
-Xmx12288m                         힙 최대 크기: 12 GB
-XX:MaxPermSize=4096m               PermGen 최대 (Java 8에서 무시됨)
-XX:+HeapDumpOnOutOfMemoryError     OOM 시 힙 덤프 자동 생성
-XX:HeapDumpPath=/usr/local/tomcat/heapdump  힙 덤프 저장 경로
```

### 3.2 옵션별 상세 설명

!!! note "-Xms8192m (초기 힙 크기)"
    ms = memory start. JVM 시작 시 OS에게 8GB 메모리를 미리 확보

    **왜 미리 확보?**

    - 런타임에 메모리 확장하면 오버헤드 발생
    - 서버는 처음부터 큰 메모리 확보가 유리
    - Xms = Xmx로 설정하면 확장/축소 없어서 더 안정적

    **우리 서버:** Xms(8GB) != Xmx(12GB) → 8GB로 시작해서 필요하면 12GB까지 확장 → 확장 시 GC 빈도 증가할 수 있음

!!! note "-Xmx12288m (최대 힙 크기)"
    mx = memory maximum. 힙이 이 크기를 초과하면 OutOfMemoryError 발생. 12288m = 12 GB

    **설정 기준:** 서버 물리 메모리의 50~75% 권장 (나머지는 OS + 메타스페이스 + 네이티브 메모리). 서버 RAM 16GB → Xmx 12GB (75%)

    **너무 크면?** Full GC 시간이 길어짐 (12GB 전체 스캔) → STW 수 초 이상 발생 가능

    **너무 작으면?** GC가 너무 자주 발생 → 결국 OOM

!!! warning "-XX:MaxPermSize=4096m"
    PermGen(영구 세대) 최대 크기: 4 GB

    **BUT: Java 8에서는 PermGen이 사라짐!** 이 옵션은 완전히 무시됨. JVM이 경고 로그를 출력할 수 있음: "ignoring option MaxPermSize=4096m; support was removed in 8.0"

    **Java 8 대체 옵션:** `-XX:MaxMetaspaceSize=512m` (메타스페이스 최대 크기). 설정 안 하면 OS 메모리 한도까지 자동 확장

    **우리 서버:** MaxPermSize 설정은 남아있지만 무의미 → Java 7에서 8로 마이그레이션할 때 옵션 정리 안 한 것

!!! tip "-XX:+HeapDumpOnOutOfMemoryError"
    OOM(OutOfMemoryError) 발생 시 자동으로 힙 덤프 생성

    **필수 설정이다.** OOM이 터지면 그 순간의 메모리 상태를 봐야 원인 분석 가능. 이 옵션 없으면 OOM 터져도 원인 파악 불가

    **주의:**

    - 힙 크기만큼 디스크 공간 필요
    - 힙 12GB → 덤프 파일 최대 12GB
    - 디스크 꽉 차면 덤프도 못 뜨고 서버도 죽음

!!! note "-XX:HeapDumpPath=/usr/local/tomcat/heapdump"
    힙 덤프 파일 저장 경로

    **실제 우리 힙 덤프:** `/usr/local/tomcat/heapdump/heapdump.hprof`, 크기: 496 MB, 생성일: 2025-12-11

    이 파일을 로컬로 가져와서 MAT으로 분석한 것

---

## 4. APM 에이전트 옵션

### 4.1 우리 서버의 APM

```
-javaagent:/usr/local/apm/intermax/jspd/lib/jspd.jar   (EXEM InterMax)
-javaagent:/root/whatap/whatap.agent-2.2.34.jar         (WhaTap)
```

### 4.2 javaagent란

!!! note "javaagent"
    **정의:** JVM 시작 시 특정 JAR 파일을 에이전트로 로드 → 바이트코드 조작(Instrumentation) 가능 → 모니터링, 프로파일링, 추적 등에 사용

    **동작:** JVM 시작 → javaagent JAR의 premain() 메서드 실행 → 클래스 로딩 시 바이트코드를 가로채서 수정 → 메서드 호출 시간 측정, 에러 추적 등

    **비유:** 공장(JVM) 입구에 감시 카메라(agent)를 설치 → 모든 제품(클래스)이 들어올 때 검사 → 작업 시간, 에러율 등을 기록

    **문제:** 에이전트도 메모리를 쓴다. EXEM: ~27 MB, WhaTap: ~5 MB. 2개 동시 실행: 불필요한 중복 + 충돌 가능성

---

## 5. 나머지 System Overview 항목 총정리

### 5.1 전체 13개 항목 해석

| # | 항목 | 값 | 판단 |
|---|------|-----|------|
| 1 | Used heap dump (힙에서 사용 중인 객체 총량) | 323.4 MB (12GB의 2.6%) | 정상 |
| 2 | Number of objects (힙의 모든 객체 수) | 5,231,251 | 정상 |
| 3 | Number of classes (로드된 모든 클래스 수) | 27,688 (정상:~20K) | 다소많음, 중복의심 |
| 4 | Number of class loaders (ClassLoader 인스턴스 수) | 4,574 (정상:10~50) | **비정상! 핵심문제** |
| 5 | Number of GC roots (GC 탐색 시작점 수) | 5,863 | 정상 |
| 6 | Format (힙 덤프 파일 포맷) | hprof (Java 표준) | - |
| 7 | JVM version (Java 버전 정보) | OpenJDK 1.8.0_392 | - |
| 8 | Time (덤프 생성 시각) | 19:37:42 GMT+9(KST) | - |
| 9 | Date (덤프 생성 날짜) | 2025-12-11 | - |
| 10 | Identifier size (객체 포인터 크기) | 64-bit (8 byte) | - |
| 11 | Compressed object pointers (포인터 압축 활성화) | true (4 byte) | 정상, 최적 |
| 12 | File path (힙 덤프 파일 경로) | heapdump.hprof | - |
| 13 | File length (파일 크기) | 496,948,848 (약 474 MB) | - |

---

## 6. 핵심 정리

!!! abstract "핵심 정리"
    **Identifier size: 64-bit**

    - 객체 주소를 8 byte로 표현
    - 64-bit JVM 필수 (힙 4GB 이상)

    **Compressed object pointers: true**

    - 64-bit인데 포인터를 4 byte로 압축
    - 힙 32GB 이하면 자동 활성화
    - 메모리 30~40% 절약
    - 우리 서버: 12GB < 32GB → 자동 활성화 (최적)

    **JVM 옵션:**

    - -Xms: 초기 힙 크기 (시작 시 확보)
    - -Xmx: 최대 힙 크기 (넘으면 OOM)
    - -XX:+HeapDumpOnOutOfMemoryError: OOM 시 덤프 생성 (필수)
    - -javaagent: 모니터링 에이전트 (우리는 2개 동시 실행 중)

    **다음 장:** MAT 리포트 완전 해석 -- 13개 항목을 종합해서 실제 분석 흐름 마스터
