# 06. 힙 덤프와 hprof 포맷

**이 장의 목표**: "Format: hprof", "File length: 496,948,848"이 뭔지 이해한다

---

## 1. 힙 덤프(Heap Dump)란

### 1.1 정의

```
힙 덤프 = 특정 시점에 JVM 힙 메모리의 모든 내용을 파일로 저장한 것

비유:
  힙 = 사무실 책상 위의 서류들
  힙 덤프 = 특정 순간에 책상 위를 통째로 사진 찍은 것

  사진(덤프)을 보면:
  → 그 순간에 뭐가 있었는지 전부 알 수 있다
  → 누가 뭘 참조하고 있었는지 알 수 있다
  → 어디서 메모리를 많이 쓰고 있었는지 알 수 있다
```

### 1.2 힙 덤프에 포함되는 것

!!! note "힙 덤프 내용물"
    **포함:**

    - 힙에 있는 모든 객체 (클래스, 필드값, 배열 등)
    - 객체 간의 참조 관계 (누가 누구를 가리키는지)
    - 클래스 정보 (어떤 클래스가 로드됐는지)
    - GC Root 정보
    - 스레드 스택 정보
    - 객체의 크기

    **불포함:**

    - 이미 GC된 객체 (이미 사라진 것)
    - 스택 프레임의 지역 변수 값 (일부만 포함)
    - 네이티브 메모리 내용
    - 메타스페이스 전체 (일부만 포함)

---

## 2. hprof 포맷

### 2.1 hprof란

```
hprof = Heap/CPU Profiling Tool
      = JVM의 힙 덤프 표준 바이너리 포맷

파일 확장자: .hprof
읽는 도구: Eclipse MAT, VisualVM, jhat, IntelliJ 등

바이너리 파일이라 텍스트 에디터로 열면 깨진다.
→ MAT 같은 전용 분석 도구가 필요
```

### 2.2 hprof 파일 내부 구조

!!! note "hprof 파일 구조"
    **[Header]**

    - 포맷 버전: "JAVA PROFILE 1.0.2"
    - Identifier 크기: 4 또는 8 byte
    - 덤프 시작 시간 (밀리초)

    **[Record 1] UTF-8 문자열**

    - 클래스명, 필드명 등의 문자열 데이터

    **[Record 2] 클래스 로드 정보**

    - 어떤 ClassLoader가 어떤 클래스를 로드했는지

    **[Record 3] 스택 트레이스**

    - 스레드별 메서드 호출 스택

    **[Record 4] 힙 덤프 데이터**

    - GC Root 정보
    - 모든 객체 인스턴스
    - 클래스 객체
    - 배열 데이터
    - 객체 간 참조 관계

    **[Record 5] 스레드 정보**

    - 스레드 목록, 상태

---

## 3. 힙 덤프 생성 방법

### 3.1 자동 생성 (OOM 발생 시)

```
JVM 옵션:
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=/usr/local/tomcat/heapdump

의미:
  OutOfMemoryError 발생하면 자동으로 힙 덤프 생성
  저장 경로: /usr/local/tomcat/heapdump/

우리 서버에 이 옵션이 설정되어 있었다:
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=/usr/local/tomcat/heapdump
```

### 3.2 수동 생성 (명령어)

```bash
# 방법 1: jmap (가장 일반적)
jmap -dump:format=b,file=heapdump.hprof <PID>

# 방법 2: jcmd (Java 8+)
jcmd <PID> GC.heap_dump /path/to/heapdump.hprof

# 방법 3: kill 시그널 (리눅스)
kill -3 <PID>  # 스레드 덤프 (힙 덤프 아님, 주의!)

# PID 찾기
jps -l  # Java 프로세스 목록
```

### 3.3 주의사항

!!! danger "힙 덤프 생성 시 주의"
    **1. Stop-The-World 발생**

    - 덤프 생성 중 애플리케이션이 멈춤
    - 힙이 크면 수십 초 ~ 수 분
    - 서비스 중에 하면 장애!

    **2. 파일 크기가 힙 크기와 비슷**

    - 12GB 힙이면 덤프도 수 GB ~ 12GB
    - 디스크 공간 확인 필수
    - 우리 서버: 힙 323MB → 덤프 496MB

    **3. 민감 정보 포함 가능**

    - 메모리에 있는 비밀번호, 토큰 등이 덤프에 포함
    - 외부 유출 주의

---

## 4. Used Heap 323MB vs File Length 496MB

### 4.1 왜 파일이 더 큰가?

```
Used heap dump:   323.4 MB (힙에서 사용 중인 객체 총량)
File length:      496,948,848 byte = 약 474 MB

차이 이유:
  1. hprof 파일에는 힙 데이터만 있는 게 아님
     → 클래스 정보, 문자열 테이블, 스택 트레이스 등 부가 정보 포함

  2. 객체 메타데이터
     → 각 객체의 클래스 참조, 필드 정보 등 오버헤드

  3. GC Root 정보, 스레드 정보 등

  4. 파일 포맷 오버헤드
     → 레코드 헤더, 타입 태그, 길이 필드 등

비유:
  Used Heap = 책 본문 글자 수
  File Length = 책 전체 (표지 + 목차 + 본문 + 색인 + 여백)
```

### 4.2 File Length 단위

```
File length: 496,948,848

이건 byte 단위다.

496,948,848 byte
= 496,948,848 / 1,024 = 485,106 KB
= 485,106 / 1,024 = 473.7 MB

약 474 MB 파일
```

---

## 5. 힙 덤프 시점 정보

```
Time: 오후 7시 37분 42초 GMT+9
Date: 2025. 12. 11.
```

### 5.1 이게 왜 중요한가

!!! note "덤프 시점의 중요성"
    **1. 서버 상태 추정**

    - 2025-12-11 19:37:42 (퇴근 시간 즈음)
    - 아직 사용자 접속이 있을 수 있는 시간
    - StandardSession 2,989개 = 약 3천 세션 활성

    **2. 서버 가동 시간 추적**

    - "서버 재기동 후 약 5일 경과"
    - 재기동: 약 12월 6~7일
    - 5일간 DelegatingClassLoader가 4,257개 누적

    **3. 문제 재현/비교**

    - 재기동 직후 덤프 vs 5일 후 덤프 비교하면
    - 뭐가 늘어났는지 정확히 알 수 있음

    **4. GMT+9**

    - 한국 시간대 (KST)
    - 서버가 한국 시간대로 설정되어 있음

---

## 6. MAT (Eclipse Memory Analyzer Tool)

### 6.1 MAT이란

```
MAT = 힙 덤프(.hprof)를 분석하는 전용 도구
Eclipse 재단에서 만든 무료 오픈소스 도구

기능:
  1. Leak Suspects:  메모리 누수 자동 탐지
  2. Dominator Tree: 메모리 점유 상위 객체 목록
  3. Histogram:      클래스별 객체 수/크기
  4. GC Roots:       특정 객체를 잡고 있는 GC Root 추적
  5. OQL:            SQL처럼 객체를 쿼리
```

### 6.2 MAT이 생성하는 인덱스 파일

```
우리 폴더에 있는 파일들:

heapdump.hprof           ← 원본 힙 덤프
heapdump.threads         ← 스레드 정보
heapdump.idx.index       ← 객체 인덱스
heapdump.o2c.index       ← 객체→클래스 매핑
heapdump.a2s.index       ← 배열→크기 매핑
heapdump.inbound.index   ← 들어오는 참조 인덱스
heapdump.outbound.index  ← 나가는 참조 인덱스
heapdump.o2hprof.index   ← 객체→hprof 위치 매핑
heapdump.index           ← 메인 인덱스
heapdump.domIn.index     ← 도미네이터 트리 (인바운드)
heapdump.o2ret.index     ← 객체→Retained Heap 매핑
heapdump.domOut.index    ← 도미네이터 트리 (아웃바운드)
heapdump.i2sv2.index     ← 인바운드 참조 v2

이 인덱스 파일들은 MAT이 처음 열 때 자동 생성한다.
→ 분석 속도를 높이기 위한 캐시
→ 원본은 heapdump.hprof 하나
```

---

## 7. 힙 덤프 vs 스레드 덤프

### 7.1 차이

| 구분 | 힙 덤프 (Heap Dump) | 스레드 덤프 (Thread Dump) |
|------|-------------------|------------------------|
| 내용 | 메모리 상태 스냅샷 | 스레드 상태 스냅샷 |
| 포함 | 객체, 참조, 크기 | 스레드 목록, 스택 트레이스 |
| 포맷 | .hprof 바이너리 파일 | 텍스트 파일 |
| 크기 | 수백 MB ~ 수 GB | 수 KB ~ 수 MB |
| 분석도구 | MAT으로 분석 | 텍스트 에디터로 분석 가능 |
| 용도 | 메모리 누수 분석용 | 데드락, 병목 분석용 |
| STW | STW 길게 발생 | STW 짧게 발생 |
| 핵심 질문 | "메모리에 뭐가 있어?" | "스레드가 뭐 하고 있어?" |

---

## 8. 핵심 정리

!!! abstract "핵심 정리"
    **힙 덤프:**

    - 특정 시점 JVM 힙의 스냅샷
    - 모든 객체, 참조, 크기 정보 포함
    - .hprof 바이너리 포맷

    **Format: hprof**

    - Java 표준 힙 덤프 포맷
    - 헤더 + 문자열 + 클래스 + 스택 + 힙데이터 구조

    **File length: 496,948,848 (약 474 MB)**

    - Used Heap(323MB)보다 큰 이유: 부가 메타데이터 포함

    **Time/Date: 2025-12-11 19:37:42 KST**

    - 덤프 시점 = 분석 기준점
    - 서버 재기동 후 약 5일 경과 시점

    **다음 장:** JVM 옵션과 튜닝 -- Identifier size, Compressed OOP 등 나머지 항목
