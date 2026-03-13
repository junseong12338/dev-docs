# 05. JVM 옵션 완전 해석 - Gamma

---

## 1. 왜 이걸 알아야 해? - "이게 뭐야?"

### 비유로 문 열기

자동차 계기판을 생각해봐.

운전 초보는 속도계만 봐. 근데 정비사는? RPM, 수온, 유압, 연료분사량 전부 본다. 계기판 숫자 하나하나가 뭘 의미하는지 알거든. 차에 이상이 생기면 "아, RPM이 불안정하고 수온이 높으니까 냉각수 문제겠다"고 추론할 수 있어.

서버도 똑같아. `ps -ef | grep java`를 치면 JVM 옵션이 한 줄로 쭉 나와. 이걸 못 읽는 개발자는 "뭔가 많네..." 하고 넘어가지. 읽을 줄 아는 개발자는 5초 만에 서버 설정 전체를 파악해.

!!! note "초보 vs 괴물 개발자의 차이"

    **초보 개발자가 ps -ef를 보면:**

    "java -Xms8192m -Xmx12288m -XX:MaxPermSize=4096m ..."
    --> "음... 자바가 돌아가고 있네... 뭔가 숫자가 크네..."
    --> 끝. 더 이상 읽을 수 없음.

    **괴물 개발자가 ps -ef를 보면:**

    --> "Java 8 OpenJDK, 초기 힙 8GB, 최대 12GB,
    MaxPermSize는 Java 8이니까 무시되겠네,
    힙덤프 설정 있고, APM 에이전트(jspd) 붙어 있고,
    톰캣이고, TLS DH 키 2048비트..."
    --> 5초 안에 서버 상태 파악 끝.

    이 차이를 만드는 게 이 챕터야.

### JVM 옵션의 본질

JVM을 실행할 때 전달하는 옵션(플래그)들이야. 이 옵션들이 JVM의 동작 방식을 결정해. 메모리를 얼마나 쓸지, 보안을 어떻게 처리할지, 로그를 어디에 남길지, 모니터링 에이전트를 붙일지 전부 여기서 결정돼.

---

## 2. 우리 서버 ps -ef 출력 원본

이거 우리 LMS 서버(WAS01, 15GB RAM, Java 8)에서 실제로 `ps -ef | grep java`로 뽑은 결과야. 한 글자도 안 바꿨어. 이걸 이 챕터에서 완전히 해부한다.

```
/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java
  -Djava.util.logging.config.file=/usr/local/tomcat/conf/logging.properties
  -Djava.util.logging.manager=org.apache.juli.ClassLoaderLogManager
  -Djdk.tls.ephemeralDHKeySize=2048
  -javaagent:/home/jspd/jspd/lib/jspd.agent.jar
  -Xms8192m
  -Xmx12288m
  -XX:MaxPermSize=4096m
  -XX:+HeapDumpOnOutOfMemoryError
  -XX:HeapDumpPath=/home/heapdump
  -Djava.protocol.handler.pkgs=org.apache.catalina.webresources
  -Dorg.apache.catalina.security.SecurityListener.UMASK=0027
  -Dignore.endorsed.dirs=
  -classpath /usr/local/tomcat/bin/bootstrap.jar:/usr/local/tomcat/bin/tomcat-juli.jar
  -Dcatalina.base=/usr/local/tomcat
  -Dcatalina.home=/usr/local/tomcat
  -Djava.io.tmpdir=/usr/local/tomcat/temp
  org.apache.catalina.startup.Bootstrap start
```

위에서 줄바꿈으로 나눴지만, 실제 ps -ef 출력에서는 한 줄이야. 보기 좋게 나눈 거야.

이 한 줄에 서버의 모든 정보가 들어 있어. 자바 버전, 톰캣 설정, 메모리 설정, 보안 설정, 모니터링 설정 전부.

---

## 3. JVM 옵션의 분류 체계 - "어떤 종류가 있어?"

JVM 옵션은 **접두사(prefix)**로 종류가 나뉘어. 접두사만 보면 "이건 어떤 성격의 옵션이구나"를 바로 알 수 있어. 처음 보는 옵션이라도 접두사만 보면 역할을 추측할 수 있다는 거야.

### 3-1. 분류 전체 구조

!!! abstract "JVM 옵션 분류 체계"

    | 접두사 | 이름 | 안정성 | 예시 |
    |--------|------|--------|------|
    | (없음, -로 시작) | 표준 옵션 | 모든 JVM 보장 | -classpath, -jar, -version |
    | -X | 비표준 옵션 | HotSpot 지원, 변경 가능 | -Xms, -Xmx, -Xss, -Xmn |
    | -XX: | 고급(실험) 옵션 | 예고 없이 변경/삭제 | -XX:+UseG1GC, -XX:MaxPermSize |
    | -D | 시스템 프로퍼티 | 자바 표준 | -Dcatalina.home, -Djava.io.tmpdir |
    | -javaagent: | 에이전트 | 자바 표준 | -javaagent:apm.jar |
    | (맨 마지막) | 메인 클래스 | - | Bootstrap start |

### 3-2. 표준 옵션 (Standard Options)

접두사가 그냥 `-`로 시작하는 옵션. 모든 JVM 구현체에서 동작이 **보장**돼. Oracle JDK, OpenJDK, IBM JDK, Azul Zulu 어디서든 똑같이 동작해.

!!! note "표준 옵션 예시"

    - **-classpath (또는 -cp)**: JVM이 클래스 파일을 찾을 경로 지정. "이 jar 파일들 안에서 클래스를 찾아라"
    - **-jar**: 실행 가능한 JAR 파일 직접 실행. `java -jar myapp.jar`
    - **-version**: JVM 버전 정보 출력. `java -version`
    - **-verbose:class / -verbose:gc**: 클래스 로딩 / GC 동작 로그를 콘솔에 출력

    **핵심: 표준 옵션은 어떤 JVM에서든 동작한다. 가장 안전하다.**

### 3-3. 비표준 옵션 (-X Options)

`-X`로 시작하는 옵션. HotSpot JVM(Oracle/OpenJDK)에서 동작하지만, 다른 JVM 구현체에서는 보장 안 돼. 다만 현실에서는 거의 모든 서버가 HotSpot 계열이라 사실상 표준처럼 쓰여.

!!! note "비표준 옵션 (-X) 예시"

    | 옵션 | 설명 |
    |------|------|
    | -Xms\<size\> | 힙 메모리 초기 크기 (minimum starting) |
    | -Xmx\<size\> | 힙 메모리 최대 크기 (maximum) |
    | -Xss\<size\> | 스레드 스택 크기 (stack size) |
    | -Xmn\<size\> | Young Generation 크기 (new generation) |

    **크기 단위:** k = 킬로바이트(KB), m = 메가바이트(MB), g = 기가바이트(GB)

    **예:** -Xms8192m = -Xms8g = 8GB / -Xmx12288m = -Xmx12g = 12GB / -Xss512k = 스레드 하나당 512KB 스택

    **핵심: 메모리 관련 핵심 옵션은 대부분 -X 계열이다. 이것만 읽을 줄 알아도 서버 메모리 설정 절반은 파악 가능.**

### 3-4. 고급 옵션 (-XX: Options)

`-XX:`로 시작하는 옵션. JVM 내부 동작을 세밀하게 제어해. **예고 없이 변경되거나 삭제**될 수 있어서 "실험적" 옵션이라고도 불러.

**문법이 2가지야. 이거 중요해:**

!!! note "고급 옵션 (-XX:) 문법"

    **[타입 1] 불린(Boolean) 타입 -- 켜기/끄기**

    - `-XX:+HeapDumpOnOutOfMemoryError` -- "+" = 켜기 (ON)
    - `-XX:-HeapDumpOnOutOfMemoryError` -- "-" = 끄기 (OFF)
    - `-XX:+UseG1GC` -- G1 GC 사용 켜기
    - `-XX:-UseCompressedOops` -- 압축 포인터 끄기

    **+는 켜기, -는 끄기. 딱 이것만 기억해.**

    **[타입 2] 값 설정 타입 -- key=value**

    - `-XX:MaxPermSize=4096m` -- PermGen 최대 크기
    - `-XX:HeapDumpPath=/home/heapdump` -- 힙덤프 저장 경로
    - `-XX:MaxMetaspaceSize=512m` -- Metaspace 최대 크기
    - `-XX:MaxGCPauseMillis=200` -- GC 목표 정지 시간 (밀리초)

    **요약: +는 켜기, -는 끄기, =는 값 설정.**

### 3-5. 시스템 프로퍼티 (-D Options)

`-D`로 시작하는 옵션. 이건 JVM 자체의 설정이 아니라, **자바 애플리케이션에 전달하는 설정값**이야. 쪽지를 건네준다고 생각해. JVM한테 "이 쪽지를 애플리케이션에 전달해"라고 하는 거야.

!!! note "시스템 프로퍼티 (-D) 동작"

    명령줄: `java -Dcatalina.home=/usr/local/tomcat MyApp`

    JVM 내부 System Properties (Map 자료구조):

    | key | value | 출처 |
    |-----|-------|------|
    | catalina.home | /usr/local/tomcat | -D로 넣은 값 |
    | os.name | "Linux" | JVM이 자동으로 넣은 값 |
    | java.version | "1.8.0_xxx" | JVM이 자동으로 넣은 값 |

    자바 코드에서 꺼내 쓰기:

    ```java
    String home = System.getProperty("catalina.home");
    // home = "/usr/local/tomcat"
    ```

    **원리:** -D로 넘기면 JVM이 내부 Properties 맵에 key=value로 저장. 애플리케이션이 System.getProperty()로 꺼내 쓰는 구조야.

### 3-6. 에이전트 옵션 (-javaagent)

`-javaagent:`로 시작하는 옵션. JVM이 시작될 때 **바이트코드를 조작**할 수 있는 에이전트 JAR을 로딩해. APM(Application Performance Management) 도구가 이 방식으로 동작해.

!!! note "-javaagent 동작 원리"

    ```mermaid
    flowchart LR
        A[".class 파일"] --> B["클래스 로더"]
        B --> C["에이전트가<br/>바이트코드 수정"]
        C --> D["JVM 메모리에 적재"]
        D --> E["실행"]
    ```

    에이전트가 끼워넣는 코드 예시:

    ```java
    // 원래 메서드:
    public void processOrder() {
        // 비즈니스 로직
    }

    // 에이전트가 수정한 후:
    public void processOrder() {
        long start = System.nanoTime();  // <-- 에이전트가 삽입
        // 비즈니스 로직 (원래 코드)
        long elapsed = System.nanoTime() - start;  // <-- 에이전트가 삽입
        agent.report(elapsed);  // <-- 에이전트가 삽입
    }
    ```

    **결과:** APM 대시보드에서 "이 API 응답시간 3초" 같은 정보가 나옴. 개발자가 코드에 직접 측정 코드를 안 넣어도 됨. 코드 수정 없이 모니터링이 가능한 이유가 바로 이거야.

### 3-7. 분류 요약 표

| 접두사 | 종류 | 대상 | 안정성 | 예시 |
|--------|------|------|--------|------|
| (없음, -) | 표준 옵션 | 모든 JVM 공통 | 보장됨 | -classpath, -jar, -version |
| -X | 비표준 옵션 | HotSpot JVM | 변경 가능 | -Xms, -Xmx, -Xss |
| -XX: | 고급 옵션 | HotSpot 내부 | 예고 없이 변경/삭제 | -XX:+UseG1GC |
| -D | 시스템 프로퍼티 | 자바 애플리케이션 | 자바 표준 | -Dcatalina.home |
| -javaagent: | 에이전트 | 바이트코드 조작 | 자바 표준 | -javaagent:apm.jar |
| (맨 마지막) | 메인 클래스 | 실행 대상 | - | Bootstrap start |

---

## 4. 옵션 하나하나 완전 해석 - "이게 다 뭐야?"

이제 우리 서버의 ps -ef 출력을 위에서 아래로, **한 줄도 빠짐없이** 해석한다.

### 4-1. Java 실행 경로

```
/usr/lib/jvm/java-8-openjdk-amd64/jre/bin/java
```

!!! note "Java 실행 경로 해석"

    | 경로 부분 | 의미 |
    |-----------|------|
    | `/usr/lib/jvm/` | 리눅스에서 JVM이 설치되는 표준 경로 |
    | `java-8-openjdk-amd64/` | Java 8, OpenJDK, 64비트 AMD 아키텍처 |
    | `jre/bin/java` | JRE의 java 실행 파일 |

    이 한 줄에서 알 수 있는 것:

    1. **Java 버전: 8** (= 1.8) -- 2014년 출시. 구버전이지만 엔터프라이즈에서 아직도 많이 씀
    2. **JDK 종류: OpenJDK** (Oracle JDK가 아님) -- Oracle JDK는 유료 라이선스 이슈가 있어서 많은 기업이 무료인 OpenJDK로 전환함
    3. **아키텍처: amd64** (= x86_64, 64비트) -- 서버는 거의 100% 64비트. 32비트면 메모리 주소를 4GB까지만 쓸 수 있어서 서버에 부적합
    4. **실행 위치: JRE 내부** (JDK가 아닌 JRE) -- JRE = Java Runtime Environment (실행만 가능), JDK = Java Development Kit (개발+실행). 서버에서는 실행만 하면 되니까 JRE만 있어도 됨

    **왜 중요해?** Java 버전에 따라 JVM 옵션이 달라져. 예: -XX:MaxPermSize는 Java 7까지만 유효하고 Java 8부터 무시. Java 버전을 모르면 옵션 해석을 잘못할 수 있어.

### 4-2. 톰캣 로깅 설정 파일 경로

```
-Djava.util.logging.config.file=/usr/local/tomcat/conf/logging.properties
```

!!! note "옵션: -Djava.util.logging.config.file (분류: -D 시스템 프로퍼티)"

    **뭘 하는 건지:** 자바의 기본 로깅 프레임워크(java.util.logging, 줄여서 JUL)에게 "설정 파일은 여기에 있어"라고 알려주는 거야.

    logging.properties 파일 안에는: 로그 레벨 (INFO, WARNING, SEVERE 등), 로그 출력 위치 (콘솔, 파일), 로그 포맷 (날짜, 클래스명, 메시지 형식) 이런 설정이 들어 있어.

    **왜 설정했는지:** 톰캣은 내부적으로 JUL을 사용해서 로그를 남겨. 이 설정 파일로 catalina.log, localhost.log 등의 로그 설정을 제어해.

    **없으면 어떻게 되는지:** JVM 기본 로깅 설정($JAVA_HOME/lib/logging.properties) 사용. 톰캣 전용 로그 설정이 안 먹혀서 로그가 이상해짐.

    **실무 팁:** 톰캣 로그가 안 나오거나 이상하면 이 파일을 확인해. 참고로 이건 톰캣 자체 로그 설정이고, 우리 앱(Spring)의 로그는 logback이나 log4j 설정에서 별도로 관리돼.

### 4-3. 톰캣 전용 로그 매니저

```
-Djava.util.logging.manager=org.apache.juli.ClassLoaderLogManager
```

!!! note "옵션: -Djava.util.logging.manager (분류: -D 시스템 프로퍼티)"

    **뭘 하는 건지:** 자바 로깅 시스템의 "관리자(Manager)"를 톰캣이 만든 커스텀 로그 매니저(JULI)로 교체하는 거야. JULI = Java Util Logging Implementation (톰캣 버전)

    **왜 커스텀 로그 매니저가 필요해?** 톰캣은 하나의 JVM에 여러 웹 애플리케이션(WAR)을 올려. 각 WAR는 자기만의 ClassLoader를 갖고 있어.

    - 자바 기본 LogManager: JVM 전체에 1개 --> 모든 WAR의 로그가 섞임
    - 톰캣 JULI LogManager: ClassLoader별로 분리 --> WAR별 로그 분리 가능

    **비유:** 건물에 사무실이 5개 있는데, 기본 로그 매니저는 건물 전체에 스피커 1개 --> 다 섞여서 들림. 톰캣 로그 매니저는 사무실마다 스피커 1개 --> 각자 따로 들림.

    catalina.sh 스크립트가 이 옵션을 자동으로 추가해. 개발자가 직접 건드릴 일은 거의 없어.

### 4-4. TLS 보안 설정

```
-Djdk.tls.ephemeralDHKeySize=2048
```

!!! note "옵션: -Djdk.tls.ephemeralDHKeySize=2048 (분류: -D 시스템 프로퍼티)"

    **용어:** TLS = Transport Layer Security (HTTPS의 보안 프로토콜) / DH = Diffie-Hellman (키 교환 알고리즘) / ephemeral = 임시 (매 연결마다 새 키를 생성) / 2048 = 키 크기 (2048비트)

    **뭘 하는 건지:** HTTPS 통신할 때 사용하는 DH 키의 크기를 2048비트로 설정. 기본값(1024비트)보다 큰 키를 사용해서 보안을 강화하는 거야.

    **왜 2048?** 1024비트는 2015년 Logjam 공격으로 취약한 것으로 판명됨. 2048비트는 현재 업계 권장 최소 크기. 4096비트는 더 안전하지만 TLS 핸드셰이크 시 성능 저하.

    **실무 팁:** 보안 점검에서 "Weak DH Key" 경고가 나오면 이 옵션이 없거나 값이 1024 이하인 경우야. 외부 API 연동(결제 등)할 때 상대방이 2048비트를 요구하면 이 설정 없이는 TLS 연결 자체가 실패할 수 있어.

### 4-5. APM 에이전트

```
-javaagent:/home/jspd/jspd/lib/jspd.agent.jar
```

!!! note "옵션: -javaagent:jspd.agent.jar (분류: Java Agent)"

    jspd = Java Server Performance Diagnostics --> 인터맥스(InterMax)라는 국산 APM 솔루션의 에이전트

    **APM이 뭐야?** Application Performance Management. 애플리케이션 성능을 실시간으로 모니터링하는 도구.

    **이 에이전트가 하는 일:**

    1. 모든 HTTP 요청의 응답 시간 측정 -- "이 API 호출에 3.2초 걸렸다"
    2. SQL 쿼리 실행 시간/횟수 추적 -- "이 쿼리가 2.1초나 걸렸다 (느린 쿼리!)"
    3. 메서드 호출 스택 추적 (프로파일링) -- "어디서 병목이 걸렸는지" 콜 스택으로 보여줌
    4. JVM 메모리/GC 상태 수집 -- 힙 사용량, GC 횟수 등을 대시보드에 표시
    5. 스레드 상태 모니터링 -- 스레드 덤프, 데드락 감지
    6. 이상 징후 감지 / 알림 -- 응답 시간 급증 시 알람

    **원리:** JVM이 클래스를 로딩할 때 에이전트가 바이트코드에 측정 코드를 끼워넣어. 개발자 코드를 수정하지 않고도 성능 데이터 수집이 가능.

    **주의:** 에이전트 자체도 CPU/메모리를 쓰기 때문에 약간의 오버헤드(보통 3~5%)가 발생해. 에이전트 JAR 파일이 없으면 JVM 시작 자체가 실패해! --> 톰캣 안 뜸 --> 서비스 장애

### 4-6. 힙 메모리 초기 크기

```
-Xms8192m
```

이거 04장에서 배운 committed 개념이랑 직결돼.

!!! danger "옵션: -Xms8192m (분류: -X 비표준 JVM 옵션)"

    **뭘 하는 건지:** JVM 힙 메모리의 "시작(초기) 크기"를 8192MB(= 8GB)로 설정. "JVM아, 시작할 때 힙을 최소 8GB 확보해라."

    **동작:** JVM이 시작되면 OS한테 8GB의 가상 메모리를 요청(committed)해. 이 시점에서 8GB가 전부 물리 RAM에 올라가는 건 아니야. 실제로 객체를 생성하면서 사용하는 부분만 물리 RAM에 올라가. (page fault --> 물리 페이지 할당, 04장에서 배운 거)

    **계산:** 8192m = 8,192 MB = 8,192 x 1,024 KB = 8,388,608 KB = 8 GB

    **왜 설정했는지:** JVM이 시작할 때부터 충분한 힙을 확보해서, 나중에 힙 확장으로 인한 성능 저하를 줄이려고.

    **없으면 어떻게 되는지:** JVM 기본값 사용 (보통 물리 RAM의 1/64 또는 256MB). 서버 앱에는 턱없이 부족해서 시작하자마자 GC 폭탄 맞음.

    **주의:** 'm'은 메가바이트, 'g'로 쓰면 기가바이트 (-Xms8g도 같은 뜻). -Xms > -Xmx로 설정하면 JVM이 아예 안 뜸 (시작 거부). JVM이 필요하면 -Xms보다 더 키울 수 있어 (-Xmx까지)

### 4-7. 힙 메모리 최대 크기

```
-Xmx12288m
```

!!! danger "옵션: -Xmx12288m (분류: -X 비표준 JVM 옵션)"

    **뭘 하는 건지:** JVM 힙 메모리의 "최대 크기"를 12288MB(= 12GB)로 설정. "JVM아, 힙을 아무리 키워도 12GB를 넘기지 마라."

    **동작:** JVM은 -Xms(8GB)로 시작해서, 힙이 부족하면 자동으로 확장해. 근데 절대로 -Xmx(12GB)를 넘지는 않아. 12GB까지 써도 모자라면? OutOfMemoryError가 터져.

    **계산:** 12288m = 12,288 MB = 12 GB

    **우리 서버 상황:**

    | 항목 | 크기 |
    |------|------|
    | 서버 총 RAM | 15 GB |
    | -Xmx (힙 최대) | 12 GB |
    | 남은 여유 | 15 - 12 = 3 GB |

    3GB로 해야 하는 일: OS 커널 자체 동작 (~0.5~1 GB) / Metaspace (~0.1~0.5 GB) / Thread Stacks (~0.2 GB, 200개x1MB) / APM Agent (~0.1~0.3 GB) / Code Cache, Native 등 (~0.2 GB). 빠듯하지만, 실제로는 힙이 12GB까지 안 차는 경우가 많아서 돌아가고 있는 거야.

    **없으면 어떻게 되는지:** JVM 기본값 (보통 물리 RAM의 1/4). 우리 서버면 약 3.75GB. LMS에는 부족해서 서비스 운영 중 OOM 터질 가능성 높음.

### 4-8. -Xms와 -Xmx의 관계 심화

이 두 옵션의 관계가 정말 중요해. 따로 이해하면 안 되고 반드시 같이 이해해야 해.

!!! note "-Xms와 -Xmx 관계 시각화"

    우리 서버: -Xms8192m -Xmx12288m (다르게 설정)

    ```
    힙 크기
    12GB ---- -Xmx (천장, 절대 못 넘음)
                                    현재 우리 서버 (11.26GB)
                              /
                         /
                    /    <-- JVM이 필요에 따라 확장
               /
          /
    8GB --  <-- 시작점 (-Xms)

         ---------------------------------> 시간
    ```

    만약 같게 설정하면 (-Xms12288m -Xmx12288m):

    ```
    12GB ---------------------------------- 시작부터 끝까지 일정
         ---------------------------------> 시간
    --> 확장/축소 없음. GC 예측 가능. 모니터링 안정.
    ```

    -Xms > -Xmx 로 설정하면 JVM이 시작을 거부함. 에러: "Initial heap size set to a larger value than the maximum heap"

| 구분 | 다르게 (-Xms < -Xmx) | 같게 (-Xms = -Xmx) |
|------|----------------------|---------------------|
| 시작 시 메모리 | 적게 차지 (8GB) | 많이 차지 (12GB) |
| 힙 확장 | 런타임에 점진 확장 발생 | 확장 없음 |
| 확장 비용 | GC + OS 추가 메모리 요청 (page fault) | 없음 |
| GC 예측 | 확장 타이밍에 GC 패턴이 변동 | 예측 가능, 일정 |
| 모니터링 | RSS가 점진적 증가 (누수와 혼동 위험) | 시작부터 안정적 |
| 메모리 절약 | 안 쓸 때 적게 차지 | 항상 최대치 점유 |
| 운영 권장 | 개발/테스트 환경 | **운영 서버 권장** |

**실무 권장**: 운영 서버에서는 **-Xms = -Xmx를 같게** 설정하는 게 일반적이야. 힙 확장 비용을 없애고, 모니터링을 안정적으로 만들기 위해서. 우리 서버처럼 다르게 설정하면 "메모리가 올라갔다!" 같은 불필요한 경보가 울릴 수 있어. 06장에서 더 자세히 다뤄.

### 4-9. PermGen 크기 (Java 8에서 무시!)

```
-XX:MaxPermSize=4096m
```

!!! danger "옵션: -XX:MaxPermSize=4096m -- Java 8에서 무시됨!"

    **이 옵션은 우리 서버(Java 8)에서 "무시"되고 있다! 실제로 아무 효과가 없어!**

    PermGen(Permanent Generation)이 뭐였냐? 클래스 메타데이터, 메서드 정보, static 변수 등을 저장하는 공간. 힙 메모리의 일부였어 (Java 7까지).

    **Java 7 이전:** Heap = Young Gen + Old Gen + PermGen. -XX:MaxPermSize로 PermGen 크기를 설정 (유효!)

    **Java 8 이후:** Heap = Young Gen + Old Gen (PermGen 삭제!). Metaspace가 Native Memory(힙 바깥)에서 대체. -XX:MaxPermSize --> 무시됨! -XX:MaxMetaspaceSize --> 이걸 써야 함.

    **왜 PermGen을 없앴어?**

    1. PermGen은 크기가 고정이라 "PermGen space" OOM이 자주 발생
    2. 클래스를 동적으로 많이 로딩하는 앱(Spring, Hibernate 등)에서 PermGen이 부족해지는 문제가 반복됐어
    3. Metaspace로 바꾸면서 네이티브 메모리를 사용하게 해서 자동 확장이 가능해짐 (기본 제한 없음)

    **우리 서버에 이 옵션이 남아 있는 이유:** 과거 Java 7 시절에 설정한 게 그대로 남아 있는 거야. JVM은 경고만 찍고 정상 동작해:

    ```
    Java HotSpot(TM) 64-Bit Server VM warning:
    ignoring option MaxPermSize=4096m; support was removed in 8.0
    ```

**PermGen vs Metaspace 비교표:**

| 구분 | PermGen (Java 7 이전) | Metaspace (Java 8+) |
|------|----------------------|---------------------|
| 위치 | 힙 메모리 내부 | 네이티브 메모리 (힙 바깥) |
| 크기 제한 | -XX:MaxPermSize로 고정 | 기본 무제한 (OS 메모리까지) |
| OOM 에러 | PermGen space | Metaspace |
| 크기 조절 | 수동으로 -XX:MaxPermSize 설정 | 자동 확장 (-XX:MaxMetaspaceSize로 상한선 가능) |
| 설정 옵션 | -XX:PermSize, -XX:MaxPermSize | -XX:MetaspaceSize, -XX:MaxMetaspaceSize |
| 문제점 | 크기 예측 어려움, OOM 자주 발생 | 제한 안 걸면 무한 확장 위험 |

### 4-10. OOM 시 힙덤프 자동 생성

```
-XX:+HeapDumpOnOutOfMemoryError
```

!!! danger "옵션: -XX:+HeapDumpOnOutOfMemoryError -- 운영 서버 필수!"

    **뭘 하는 건지:** OutOfMemoryError가 발생하면 자동으로 힙덤프 파일을 생성해. 힙덤프 = 그 순간 JVM 힙에 있는 모든 객체를 .hprof 파일로 저장한 것. MAT(Memory Analyzer Tool) 같은 도구로 분석 가능.

    **비유:** 비행기 블랙박스야. 추락(OOM) 했을 때 원인 분석을 위한 증거물. 블랙박스 없이 추락하면 "왜 떨어졌는지 모르겠어요"밖에 못 해.

    **왜 중요해?** OOM이 터지면 서버가 죽거나 불안정해져. 근데 왜 OOM이 터졌는지 모르면 재발 방지를 못 해. 나중에 재현이 안 될 수도 있으니까, 터지는 순간 자동으로 덤프를 떠놓는 거야.

    **없으면 어떻게 되는지:** OOM 터져도 힙덤프 안 남음. "왜 터졌어?" --> "몰라, 다시 안 터지길 기도해..." 이런 상황이 됨.

    **운영 서버에서는 반드시 켜놔야 하는 옵션. 이거 없으면 장애 분석 불가능.**

    **주의:** 힙덤프 생성 중에 JVM이 멈춤 (수십 초~수 분). 덤프 파일 크기 = 힙 사용량과 비슷 (수 GB 될 수 있음)

### 4-11. 힙덤프 저장 경로

```
-XX:HeapDumpPath=/home/heapdump
```

!!! warning "옵션: -XX:HeapDumpPath=/home/heapdump"

    **뭘 하는 건지:** OOM 발생 시 힙덤프 파일이 /home/heapdump 디렉토리에 생성됨. 파일명 형식: `java_pid<PID>.hprof` (예: java_pid12345.hprof)

    **없으면 어떻게 되는지:** JVM 실행 디렉토리(working directory)에 떨어짐. 톰캣의 경우 보통 bin/ 디렉토리인데, 관리가 어려워. 전용 디렉토리에 모아놓으면 찾기 쉽고 디스크 관리도 편해.

    **주의사항 (진짜 중요):**

    1. 힙덤프 파일 크기 = 최대 -Xmx까지! 우리 서버: 최대 12GB짜리 파일이 생길 수 있어! `df -h /home/heapdump`으로 여유 공간 확인
    2. 같은 경로에 이미 파일이 있으면 덮어쓰지 않아. OOM 발생 후 파일을 다른 곳으로 옮겨놔야 해
    3. 디렉토리가 존재해야 함 (자동 생성 안 됨). 디렉토리 없으면 덤프 생성 실패
    4. 쓰기 권한 필요. 톰캣 실행 유저가 해당 경로에 쓸 수 있어야 함

### 4-12. 프로토콜 핸들러

```
-Djava.protocol.handler.pkgs=org.apache.catalina.webresources
```

!!! note "옵션: -Djava.protocol.handler.pkgs (분류: -D 시스템 프로퍼티)"

    **뭘 하는 건지:** 자바에서 URL을 처리할 때, 어떤 패키지에서 프로토콜 핸들러를 찾을지 지정. org.apache.catalina.webresources = 톰캣의 웹 리소스 처리 패키지. WAR 파일 안의 리소스를 URL로 접근할 수 있게 해줌.

    톰캣 8+ 이상에서 필요한 설정이고, catalina.sh가 자동 추가해. 개발자가 직접 건드릴 일은 거의 없어.

### 4-13. 보안 UMASK 설정

```
-Dorg.apache.catalina.security.SecurityListener.UMASK=0027
```

!!! note "옵션: -D...SecurityListener.UMASK=0027 (분류: -D 시스템 프로퍼티)"

    UMASK = 새로 생성되는 파일의 기본 권한을 제한하는 마스크

    **0027 의미:** 0 = 특수 권한 없음 / 0 = 소유자(owner): 제한 없음 (rwx 전부) / 2 = 그룹(group): 쓰기만 제한 (r-x) / 7 = 기타(others): 전부 제한 (---)

    **결과:** 파일: 666 - 027 = 640 (rw-r-----) / 디렉토리: 777 - 027 = 750 (rwxr-x---). 톰캣이 만드는 파일을 다른 사용자가 못 읽게 하는 보안 설정.

    톰캣의 SecurityListener가 시작 시 이 UMASK 값을 체크해서 너무 느슨하면 경고를 출력해.

### 4-14. Endorsed 디렉토리 무시

```
-Dignore.endorsed.dirs=
```

!!! note "옵션: -Dignore.endorsed.dirs= (빈 값) (분류: -D 시스템 프로퍼티)"

    **Endorsed Standards Override Mechanism:** 옛날 Java에서 JDK 표준 라이브러리의 일부를 외부 JAR로 교체하는 기능. Java 9부터 완전히 제거됨.

    빈 값(=) → endorsed 디렉토리를 무시하겠다는 뜻.

    **톰캣이 이 옵션을 넣는 이유:** endorsed 디렉토리 관련 경고 메시지를 없애기 위해. catalina.sh가 자동으로 추가하는 설정이야. 기능적으로는 "아무 것도 안 함". 개발자가 건드릴 일 없어.

### 4-15. 클래스패스

```
-classpath /usr/local/tomcat/bin/bootstrap.jar:/usr/local/tomcat/bin/tomcat-juli.jar
```

!!! note "옵션: -classpath (= -cp) (분류: 표준 옵션)"

    **뭘 하는 건지:** JVM이 클래스 파일(.class)이나 JAR 파일을 찾을 경로를 지정.

    경로 구분자: `:` (리눅스), `;` (윈도우)

    **지정된 JAR 2개:**

    1. **bootstrap.jar** → 톰캣의 부트스트랩 로더. 톰캣 시작에 필요한 최소한의 클래스가 들어 있어. 이 안에 메인 클래스(Bootstrap)가 있어 (4-18에서 설명)
    2. **tomcat-juli.jar** → 톰캣의 로깅 구현체 (4-3에서 설명한 JULI). 클래스패스에 있어야 로그 매니저가 동작해

    **"겨우 2개?"** 톰캣은 자체 클래스로더 구조가 있어. 시작에 필요한 최소한만 시스템 classpath에 넣고, 나머지 라이브러리(lib/, webapps/)는 톰캣이 자체 클래스로더로 동적 로딩해. 이래야 웹앱 간 라이브러리 격리가 됨.

    **비유:** 자동차 시동 걸 때 키(bootstrap.jar)만 있으면 돼. 나머지 부품(나머지 JAR)은 엔진 걸리고 나면 알아서 동작.

    **없으면 어떻게 되는지:** JVM이 Bootstrap 클래스를 못 찾아서 시작 불가. "Error: Could not find or load main class" 에러.

### 4-16. 톰캣 경로 설정 (catalina.base / catalina.home)

```
-Dcatalina.base=/usr/local/tomcat
-Dcatalina.home=/usr/local/tomcat
```

!!! note "옵션: -Dcatalina.base, -Dcatalina.home (분류: -D 시스템 프로퍼티)"

    - **catalina.home** = 톰캣 "설치" 디렉토리 (바이너리가 있는 곳) → bin/, lib/ 등 톰캣 공통 파일
    - **catalina.base** = 톰캣 "인스턴스" 디렉토리 (설정/데이터가 있는 곳) → conf/, logs/, webapps/, temp/, work/

    보통은 둘 다 같은 경로야 (우리 서버처럼). 다른 경우는 이런 상황:

    **톰캣 하나 설치 → 여러 인스턴스 실행:**

    - `catalina.home = /opt/tomcat` (설치, 공유)
    - `catalina.base = /var/tomcat/instance1` (인스턴스1의 설정/로그)
    - `catalina.base = /var/tomcat/instance2` (인스턴스2의 설정/로그)
    - → 실행 파일(home)은 공유하고, 설정/데이터(base)는 분리하는 구조

    **우리 서버:** home = base = /usr/local/tomcat → 톰캣 하나만 돌리고 있다는 뜻. Docker 컨테이너 환경에서 흔한 설정.

    **없으면 어떻게 되는지:** 톰캣이 conf/server.xml 등을 못 찾아서 시작 실패.

### 4-17. 임시 파일 경로

```
-Djava.io.tmpdir=/usr/local/tomcat/temp
```

!!! note "옵션: -Djava.io.tmpdir=/usr/local/tomcat/temp (분류: -D 시스템 프로퍼티)"

    **뭘 하는 건지:** Java에서 File.createTempFile() 등으로 임시 파일을 만들 때 사용하는 디렉토리를 지정.

    - **기본값:** /tmp (리눅스 시스템 임시 디렉토리)
    - **우리 설정:** /usr/local/tomcat/temp (톰캣 전용 임시 디렉토리)

    **왜 /tmp 안 쓰고 별도로 설정하냐?**

    1. /tmp는 시스템 전체가 공유 → 다른 프로세스와 충돌 가능
    2. 일부 리눅스에서 /tmp를 주기적으로 비워버림 → 톰캣이 사용 중인 임시 파일이 날아갈 수 있어
    3. 톰캣 전용 temp에 두면 관리가 편해

    **이 디렉토리에 저장되는 것들:** 파일 업로드 시 멀티파트 임시 저장 파일, JSP 컴파일 결과 (일부), 세션 직렬화 데이터 등

    **주의: 이 디렉토리 디스크가 꽉 차면 파일 업로드가 안 돼!**

### 4-18. 메인 클래스와 인수

```
org.apache.catalina.startup.Bootstrap start
```

!!! note "옵션: org.apache.catalina.startup.Bootstrap start (분류: 메인 클래스 + 실행 인수)"

    **org.apache.catalina.startup.Bootstrap** → 톰캣의 메인 클래스. 이 클래스의 main() 메서드가 실행됨. bootstrap.jar 안에 들어 있어 (4-15에서 classpath로 지정)

    **start** → main() 메서드에 전달되는 인수 (args[0] = "start"). "톰캣을 시작해라"라는 명령

    ps -ef에서 맨 마지막에 있는 게 항상 "메인 클래스 + 인수"야. 앞의 모든 -D, -X, -XX 옵션은 JVM 설정이고, 마지막에 오는 이게 "뭘 실행할 건지"야.

    **실행 흐름:**

    ```
    java [JVM 옵션들...] Bootstrap start
      └→ Bootstrap.main(["start"])
           └→ 톰캣 초기화
                └→ server.xml 로드
                     └→ 커넥터(HTTP/AJP), 호스트, 엔진 구성
                          └→ webapps/ 아래 WAR 배포
                               └→ 서비스 시작! 요청 대기.
    ```

    **다른 인수:** start(톰캣 시작), stop(톰캣 중지), configtest(설정 파일 문법 검사)

---

## 5. ps -ef 출력 전체 구조 정리

전체를 한 번에 보면 이런 구조야:

!!! abstract "ps -ef 출력의 구조 (전체 조감도)"

    ```
    /usr/lib/jvm/.../java                    ← [1] 실행 파일 경로
                                                Java 8 OpenJDK 64비트

    [시스템 프로퍼티 -D: 로깅/보안]
      -Djava.util.logging.config.file=...    ← [2] 로깅 설정 파일
      -Djava.util.logging.manager=...        ← [3] 톰캣 로그 매니저
      -Djdk.tls.ephemeralDHKeySize=2048      ← [4] TLS 보안 강화

    [에이전트]
      -javaagent:.../jspd.agent.jar          ← [5] APM 에이전트(InterMax)

    [메모리 설정 -X]
      -Xms8192m                              ← [6] 초기 힙 8GB
      -Xmx12288m                             ← [7] 최대 힙 12GB

    [고급 옵션 -XX]
      -XX:MaxPermSize=4096m                  ← [8] 무시됨! (Java 8)
      -XX:+HeapDumpOnOutOfMemoryError        ← [9] OOM 힙덤프 ON
      -XX:HeapDumpPath=/home/heapdump        ← [10] 덤프 저장 경로

    [시스템 프로퍼티 -D: 톰캣 내부]
      -Djava.protocol.handler.pkgs=...       ← [11] WAR 프로토콜 핸들러
      -Dorg.apache...UMASK=0027              ← [12] 파일 보안 마스크
      -Dignore.endorsed.dirs=                ← [13] endorsed 무시

    [클래스패스]
      -classpath bootstrap.jar:tomcat-juli.jar ← [14] 시작용 JAR 2개

    [시스템 프로퍼티 -D: 톰캣 경로]
      -Dcatalina.base=/usr/local/tomcat      ← [15] 인스턴스 경로
      -Dcatalina.home=/usr/local/tomcat      ← [16] 설치 경로
      -Djava.io.tmpdir=.../temp              ← [17] 임시 파일 경로

    [메인 클래스 + 인수]
      o.a.c.startup.Bootstrap start          ← [18] 톰캣 시작!
    ```

---

## 6. 메모리 관련 옵션 심화 - "이건 꼭 알아야 해"

ps -ef에 나온 옵션 말고도, 메모리 관련해서 꼭 알아야 하는 옵션이 있어.

### 6-1. -Xss (스레드 스택 크기)

우리 서버에는 이 옵션이 없어. 없으면 기본값을 쓴다는 뜻이야. 근데 이게 뭔지는 반드시 알아야 해.

!!! danger "-Xss: 스레드 스택 크기"

    **-Xss** = 스레드 하나당 할당되는 스택 메모리 크기. Linux 64비트 Java 8 기본값: **1MB (= 1024KB)**

    **스레드 스택에 저장되는 것:** 메서드 호출 정보 (call stack frame), 지역 변수 (int, String 등의 참조값), 메서드 매개변수, 리턴 주소 (어디로 돌아갈지)

    **!! 핵심: 힙 메모리(-Xmx)에 포함되지 않는다! !!**

    **계산:** 톰캣 기본 스레드 최대 200개 가정 → 200 스레드 x 1MB = **200MB** (힙 바깥에서 추가로 소비!)

    `총 메모리 사용량 = 힙(-Xmx) + (스레드 수 x Xss) + Metaspace + ...` → -Xmx만 보면 실제 메모리 사용량을 과소 예측하게 돼

    **스택이 부족하면:** java.lang.StackOverflowError 발생. 재귀 호출이 너무 깊거나, 호출 체인이 길 때. Spring + JPA + 복잡한 비즈니스 로직 조합이면 호출 깊이가 깊어질 수 있어.

    - -Xss를 너무 작게 잡으면: StackOverflowError 위험
    - -Xss를 너무 크게 잡으면: 스레드 수 x 큰 값 = 메모리 낭비
    - → 기본값(1MB) 쓰는 게 보통 가장 안전해.

### 6-2. -Xmn (Young Generation 크기)

이것도 우리 서버에는 없지만 알아야 하는 옵션이야. 06장에서 Young Generation을 자세히 다루지만, 옵션 해석 차원에서 여기서 짚고 간다.

!!! note "-Xmn: Young Generation 크기"

    **-Xmn** = Young Generation(Eden + Survivor0 + Survivor1)의 크기. 지정하지 않으면: JVM이 알아서 결정 (보통 힙의 1/3 ~ 1/4)

    **Young Gen이 크면:**

    - (+) Minor GC 간격이 길어짐 (Eden이 크니까 덜 자주 참)
    - (-) Minor GC 한 번에 걸리는 시간이 길어짐 (더 많은 객체 스캔)
    - (-) Old Gen이 작아짐 → Full GC 더 자주 발생 가능

    **Young Gen이 작으면:**

    - (-) Minor GC가 자주 발생
    - (+) Minor GC 한 번은 빨리 끝남
    - (+) Old Gen에 더 많은 공간

    보통은 JVM에게 맡기는 게 제일 나아. GC 튜닝은 측정 → 분석 → 변경 → 재측정 사이클이야. 감으로 하면 더 나빠질 수 있어.

---

## 7. 운영에서 자주 쓰는 추가 JVM 옵션들

우리 서버 ps -ef에는 없지만, 다른 서버에서 자주 보이는 옵션들이야. 이것들도 알아야 다른 서버의 ps -ef를 읽을 때 당황 안 해.

### 7-1. GC 알고리즘 선택

!!! note "GC 알고리즘 선택 옵션"

    **-XX:+UseSerialGC** → 단일 스레드 GC. 클라이언트 앱이나 테스트용. 운영 서버에서 절대 쓰면 안 돼.

    **-XX:+UseParallelGC** → 멀티 스레드로 병렬 GC. Java 8 기본값. 처리량(throughput) 중심. STW 시간은 길 수 있음. 우리 서버 기본값! (GC 옵션을 명시적으로 안 잡았으니까)

    **-XX:+UseConcMarkSweepGC (CMS)** → 동시(concurrent) 마킹. STW 시간 줄이는 게 목표. Java 9에서 deprecated, Java 14에서 제거.

    **-XX:+UseG1GC** → G1 (Garbage First). 큰 힙(4GB+)에 적합. Java 9부터 기본값. STW 시간 목표를 설정 가능 (`-XX:MaxGCPauseMillis=200`). 우리 서버 힙(12GB)이면 G1으로 바꾸는 게 이득일 수 있어.

    **-XX:+UseZGC (Java 11+)** → 초저지연 GC. STW < 10ms 목표. 대규모 힙(수십GB~TB급)에 적합.

    **-XX:+UseShenandoahGC (Java 12+)** → ZGC와 비슷한 목표. OpenJDK에서 제공.

    **우리 서버:** Java 8 + GC 옵션 미지정 = Parallel GC (기본값) 사용 중. 12GB 힙에 Parallel GC면 Full GC 시 STW가 수 초 걸릴 수 있어. 07장(GC의 모든 것)에서 자세히 다뤄.

### 7-2. Metaspace 관련

!!! warning "Metaspace 관련 옵션"

    **-XX:MetaspaceSize=256m** → Metaspace 초기 크기 (이 크기까지 차면 GC 시도). 기본값: 약 20MB (의외로 작아!)

    **-XX:MaxMetaspaceSize=512m** → Metaspace 최대 크기. 기본값: **제한 없음!** (OS 메모리가 허용하는 한 무한 확장)

    **왜 위험해?** MaxMetaspaceSize를 안 걸어두면 클래스 로딩 누수(ClassLoader Leak) 시 네이티브 메모리를 끝없이 먹을 수 있어. → 서서히 OS 메모리를 잠식하다가 갑자기 서버 다운. → 제한을 걸면 OOM으로 빠르게 발견 가능.

    **우리 서버 상황:**

    - -XX:MaxPermSize=4096m → 무시됨 (Java 8)
    - -XX:MaxMetaspaceSize → 설정 없음!
    - 결론: Metaspace 제한이 안 걸려 있는 상태
    - **운영 개선 포인트야.**

### 7-3. GC 로그 관련

!!! tip "GC 로그 관련 옵션 (Java 8)"

    - **-verbose:gc** → GC 발생 시 기본 정보 출력 (콘솔)
    - **-XX:+PrintGCDetails** → GC 상세 정보 출력 (각 영역별 변화량)
    - **-XX:+PrintGCDateStamps** → GC 로그에 날짜/시간 포함. 없으면 JVM 시작 후 경과 시간(초)만 나옴 → 분석 어려움
    - **-Xloggc:/var/log/gc.log** → GC 로그를 파일로 저장 (콘솔 대신)
    - **-XX:+UseGCLogFileRotation / NumberOfGCLogFiles=5 / GCLogFileSize=20M** → GC 로그 파일 롤링 (20MB씩, 5개까지 유지, 오래된 것 삭제)

    **운영 서버 권장 설정 조합 (Java 8):**

    ```
    -verbose:gc
    -XX:+PrintGCDetails
    -XX:+PrintGCDateStamps
    -Xloggc:/var/log/tomcat/gc.log
    -XX:+UseGCLogFileRotation
    -XX:NumberOfGCLogFiles=5
    -XX:GCLogFileSize=20M
    ```

    **우리 서버: GC 로그 옵션이 하나도 없어!** → GC 이벤트가 어디에도 기록되지 않고 있는 상태. → "서버가 간헐적으로 느려요" 할 때 Full GC 때문인지 확인 불가. → **운영 개선 포인트.**

---

## 8. 함정과 실수 - "이거 모르면 당한다"

!!! danger "자주 당하는 함정 6가지"

    **함정 1: MaxPermSize가 Java 8에서 효과 있다고 착각**

    - 착각: "MaxPermSize=4GB 잡았으니까 PermGen이 4GB까지 쓸 수 있겠지"
    - 현실: Java 8에서 PermGen은 삭제됨. 이 옵션은 무시됨.
    - 해결: `-XX:MaxMetaspaceSize=512m` 으로 교체

    **함정 2: -Xmx를 서버 RAM과 같게 설정**

    - 착각: "RAM 15GB니까 -Xmx15g!"
    - 현실: JVM은 힙 외에도 메모리를 쓰거든! Metaspace + Thread Stack + Native + OS 자체 사용. 이것들 합치면 힙 외로 1~3GB 더 필요해. 15GB 전부 힙에 주면 나머지가 없잖아. → swap 발생 → 서버 극심한 성능 저하. → 최악의 경우 OOM Killer가 톰캣 강제 종료
    - 해결: -Xmx는 RAM의 70~80% 까지만. 나머지는 OS + 비힙용.

    **함정 3: -Xms와 -Xmx 차이가 큰데 "누수"로 오해**

    - 착각: "모니터링에서 메모리가 계속 올라가요! 누수 아니에요?"
    - 현실: JVM이 정상적으로 힙을 확장하는 것일 수 있어. -Xms와 -Xmx가 다르면 중간에 확장이 일어나거든.
    - 해결: 같게 설정하거나, jstat으로 GC 후 Old 사용량 추이 확인.

    **함정 4: HeapDumpPath에 디스크 공간 없음**

    - 착각: "HeapDump 설정 했으니 OOM 나면 덤프 뜨겠지"
    - 현실: /home/heapdump 파티션에 공간 없으면 생성 실패. 힙덤프 크기는 최대 12GB까지 될 수 있어!
    - 해결: `df -h /home/heapdump` 로 여유 공간 정기 확인. 기존 .hprof 파일이 있으면 옮기거나 삭제.

    **함정 5: -javaagent JAR가 없으면 JVM이 안 뜸**

    - 착각: "에이전트 빼면 그냥 모니터링만 안 되겠지"
    - 현실: JAR 파일이 없으면 JVM 시작 자체가 실패! → 톰캣 안 뜸 → 서비스 장애
    - 해결: 에이전트 제거 시 반드시 JVM 옵션에서도 제거.

    **함정 6: GC 로그 안 남기고 운영**

    - 착각: "GC 로그 없어도 되지 뭐"
    - 현실: "서버가 간헐적으로 느려요" → Full GC 때문인지 확인 불가. GC 로그 없으면 "왜 느렸는지" 사후 분석 불가능.
    - 해결: GC 로그 옵션 추가 (7-3 참고).

---

## 9. 우리 서버 설정 진단 - "이 설정 괜찮은 거야?"

!!! abstract "WAS01 JVM 설정 진단 결과"

    | 항목 | 현재 설정 | 판정 | 비고 |
    |------|-----------|------|------|
    | Java 버전 | Java 8 OpenJDK | 정상 | 구버전이지만 안정적 |
    | -Xms | 8192m (8GB) | 정상 | |
    | -Xmx | 12288m (12GB) | 정상 | RAM의 80% |
    | -Xms != -Xmx | 8GB != 12GB | 주의 | 힙 확장 발생, 모니터링 혼란 |
    | -XX:MaxPermSize | 4096m | 불필요 | Java 8에서 완전 무시됨 |
    | HeapDump 설정 | ON + 경로 지정 | 좋음 | 디스크 여유 확인 필요 |
    | GC 알고리즘 | 미지정 (Parallel) | 주의 | 12GB 힙이면 G1 검토 필요 |
    | GC 로그 | 없음 | 부족 | 운영 서버에는 필수 |
    | Metaspace 제한 | 없음 | 주의 | 무제한 확장 위험 있음 |
    | APM 에이전트 | jspd (InterMax) | 좋음 | 성능 모니터링 가능 |
    | TLS 보안 | DH 2048비트 | 좋음 | 업계 권장 수준 |

**개선 권장 사항 5가지:**

1. **-Xms = -Xmx 동일 설정 검토** -- 힙 확장으로 인한 불필요한 GC/모니터링 혼란 제거
2. **-XX:MaxPermSize 제거** -- 의미 없는 옵션. 경고 로그만 불필요하게 남김
3. **-XX:MaxMetaspaceSize 추가** -- 무제한 확장 방지. 클래스 로더 누수 시 빠른 감지
4. **GC 로그 옵션 추가** -- 장애 사후 분석의 핵심 자료. 반드시 필요
5. **G1 GC 전환 검토** -- 12GB 힙에는 Parallel보다 G1이 STW 시간을 줄일 수 있음

---

## 10. 정리

### 전체 옵션 분류 요약표

| 분류 | 접두사 | 우리 서버 옵션 | 핵심 |
|------|--------|----------------|------|
| 표준 | -classpath | bootstrap.jar, tomcat-juli.jar | 시작용 JAR |
| 비표준 (-X) | -Xms, -Xmx | 8GB, 12GB | 힙 크기 |
| 고급 (-XX:) | MaxPermSize, HeapDump | 덤프 ON, 경로 지정 | OOM 대비 |
| 시스템 프로퍼티 (-D) | catalina.*, logging.*, tls.* | 톰캣/로깅/보안 | 앱 설정 전달 |
| 에이전트 | -javaagent | jspd.agent.jar | APM 모니터링 |
| 메인 클래스 | (맨 마지막) | Bootstrap start | 톰캣 시작 |

### 핵심 요약 표

| 개념 | 한 줄 정리 |
|------|-----------|
| **JVM 옵션 분류** | 접두사(없음/-X/-XX:/-D/-javaagent)로 종류가 나뉜다 |
| **-Xms** | 힙 초기 크기. 시작 시 OS한테 committed 하는 양 |
| **-Xmx** | 힙 최대 크기. 이 벽을 넘으면 OOM |
| **-Xms = -Xmx** | 같게 설정하면 힙 확장 없음. 운영 서버 권장 |
| **MaxPermSize** | Java 8에서 무시됨. PermGen이 Metaspace로 대체 |
| **HeapDump** | OOM 시 블랙박스. 운영 서버 필수 |
| **-javaagent** | 바이트코드 조작으로 APM 동작. JAR 없으면 JVM 안 뜸 |
| **비힙 메모리** | 힙(-Xmx) 외에 스택, Metaspace, Native 등이 추가로 필요 |

### 이 챕터에서 반드시 기억할 것

!!! danger "이 챕터에서 반드시 기억할 것"

    1. JVM 옵션은 접두사(-X, -XX:, -D, -javaagent)로 분류된다.
    2. -Xms는 초기 힙, -Xmx는 최대 힙. 같게 설정하면 확장 없음.
    3. -XX:MaxPermSize는 Java 8에서 무시된다 (Metaspace로 대체).
    4. +HeapDumpOnOutOfMemoryError는 운영 서버 필수 옵션이다.
    5. ps -ef 한 줄만 읽어도 서버 설정을 전부 파악할 수 있다.
    6. JVM은 힙(-Xmx) 외에도 메모리를 쓴다 (스택, Metaspace 등).

### 한 줄 정리

> **ps -ef의 JVM 옵션 한 줄 한 줄이 "이 서버가 어떻게 설정돼 있는지"를 말한다. 접두사(-D, -X, -XX, -javaagent)만 구분할 줄 알면 처음 보는 옵션도 역할을 추측할 수 있다.**

---

### 확인 문제 (5문제)

> 다음 문제를 풀어봐. 답 못 하면 위에서 다시 읽어.

**Q1.** ps -ef 출력에서 `-XX:MaxPermSize=4096m`이 보인다. 우리 서버가 Java 8인데, 이 설정은 실제로 동작하고 있는가? 이유를 설명해봐.

**Q2.** 서버 RAM이 15GB인데 `-Xmx=15g`로 설정하면 안 되는 이유를 3가지 말해봐.

**Q3.** `-XX:+HeapDumpOnOutOfMemoryError`와 `-XX:HeapDumpPath`를 둘 다 설정했는데, OOM이 터졌을 때 힙덤프가 안 생겼다. 가능한 원인 2가지를 말해봐.

**Q4.** `-Xms8192m -Xmx12288m`으로 설정된 서버에서 모니터링 도구가 "메모리 사용량이 55%에서 75%로 올랐다"고 보고했다. 이것만으로 메모리 누수라고 판단할 수 있는가?

**Q5.** 다음 JVM 옵션을 분류(표준/비표준/고급/시스템 프로퍼티/에이전트)해봐:
- (A) -Xmx4g
- (B) -Dcatalina.home=/usr/local/tomcat
- (C) -XX:+UseG1GC
- (D) -classpath /lib/app.jar
- (E) -javaagent:/opt/agent.jar

??? success "정답 보기"

    **A1.** 동작하지 않는다. Java 8에서 PermGen(Permanent Generation)은 제거되고 Metaspace로 대체되었다. -XX:MaxPermSize는 Java 7 이전에만 유효하며, Java 8에서는 JVM이 이 옵션을 무시하고 경고 메시지("ignoring option MaxPermSize=4096m; support was removed in 8.0")를 출력한다. Metaspace를 제한하려면 -XX:MaxMetaspaceSize를 사용해야 한다. 우리 서버에 이 옵션이 남아 있는 건 Java 7에서 8로 업그레이드하면서 설정을 안 지운 잔재다.

    **A2.** (1) JVM은 힙(-Xmx) 외에도 Metaspace, Thread Stack, Code Cache, Native Memory 등 비힙 메모리를 사용한다. 힙만 15GB 잡으면 비힙 메모리(보통 1~3GB)를 위한 공간이 없다. (2) OS 자체도 동작에 메모리가 필요하다(커널, 파일 캐시 등). 약 0.5~1GB는 OS용으로 남겨야 한다. (3) 물리 RAM을 100% committed 하면 swap이 발생하거나, 최악의 경우 OOM Killer가 프로세스를 강제 종료할 수 있다.

    **A3.** (1) HeapDumpPath로 지정한 경로(/home/heapdump)의 디스크에 여유 공간이 부족한 경우. 힙덤프 크기는 최대 -Xmx(12GB)까지 될 수 있으므로, 그만큼의 디스크 여유가 필요하다. (2) 같은 경로에 이전 OOM 시 생성된 힙덤프 파일(java_pid<PID>.hprof)이 이미 존재하는 경우. 같은 이름의 파일이 있으면 덮어쓰지 않아서 새 파일이 생성되지 않는다.

    **A4.** 메모리 누수라고 판단할 수 없다. -Xms(8GB)와 -Xmx(12GB)가 다르게 설정돼 있으므로, JVM이 8GB에서 시작해서 트래픽 증가에 따라 정상적으로 힙을 확장하는 과정일 수 있다. 힙 확장은 JVM의 정상 동작이다. 메모리 누수를 판단하려면 JVM 내부에서 Full GC 후에도 Old Generation 사용량이 계속 증가하는지를 jstat -gc로 확인해야 한다. GC 후 줄어들면 정상, 안 줄어들면 그때 누수를 의심해야 한다.

    **A5.** (A) -Xmx4g -- 비표준 옵션 (-X 접두사). (B) -Dcatalina.home -- 시스템 프로퍼티 (-D 접두사). (C) -XX:+UseG1GC -- 고급(실험) 옵션 (-XX: 접두사). (D) -classpath -- 표준 옵션 (- 접두사, 모든 JVM에서 동작 보장). (E) -javaagent -- 에이전트 옵션 (-javaagent: 접두사).
