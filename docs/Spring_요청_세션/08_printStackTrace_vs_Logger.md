# 08. e.printStackTrace() vs Logger

**난이도**: Delta | **예상 시간**: 25분

---

## e.printStackTrace()가 뭘 하는 놈이냐

```java
catch(Exception e) {
    e.printStackTrace();  // ← 이 한 줄
}
```

이 코드가 실행되면:

1. 예외의 **전체 스택 트레이스** (호출 경로)를 문자열로 만든다
2. **System.err** 스트림에 출력한다
3. Tomcat에서 System.err는 → **catalina.out** 파일로 간다

!!! warning "문제점 요약"
    | 항목 | e.printStackTrace() | Logger (SLF4J/Log4j) |
    |------|--------------------|--------------------|
    | **출력 대상** | System.err → catalina.out | 설정된 로그 파일 |
    | **로그 레벨** | 없음 (무조건 출력) | ERROR, WARN, INFO, DEBUG |
    | **파일 로테이션** | 없음 (계속 쌓임) | 일별/크기별 자동 분리 |
    | **포맷** | 날짜/시간 없는 원시 출력 | 타임스탬프, 클래스명, 쓰레드 포함 |
    | **필터링** | 불가능 | 레벨별 on/off 가능 |
    | **성능** | synchronized (쓰레드 블로킹) | 비동기 가능 |

---

## 출력 비교

### e.printStackTrace() 출력

```
egovframework.mediopia.lxp.common.comm.exception.SessionBrokenException: system.fail.session.expire
	at egovframework.mediopia.lxp.common.comm.util.security.SecurityUtil.authorizationCheck(SecurityUtil.java:150)
	at egovframework.mediopia.lxp.common.comm.util.security.SecurityUtil.authorizationCheckRunner(SecurityUtil.java:78)
	at egovframework.mediopia.lxp.common.comm.interceptor.AuthenticInterceptor.preHandle(AuthenticInterceptor.java:69)
	at org.springframework.web.servlet.HandlerExecutionChain.applyPreHandle(HandlerExecutionChain.java:134)
	at org.springframework.web.servlet.DispatcherServlet.doDispatch(DispatcherServlet.java:958)
	... (약 30줄 더)
```

날짜도 없다. 시간도 없다. 어떤 사용자인지도 모른다. 그냥 스택 트레이스만 35줄 뿌려놓는다.

### Logger 출력

```
2026-03-15 10:23:45.123 [http-nio-8080-exec-15] ERROR
  c.m.l.c.c.interceptor.AuthenticInterceptor
  - Auth check failed: system.fail.session.expire
```

**1줄**에 날짜, 시간, 쓰레드, 클래스, 메시지가 다 들어있다.

---

## 5가지 문제점 상세

### 1. 로그 레벨 제어 불가

```java
// Logger 쓰면
log.debug("디버깅용 상세 정보");   // 운영 환경에서 끔
log.info("일반 정보");             // 필요시 끔
log.warn("주의 필요");             // 보통 킴
log.error("에러 발생: {}", e.getMessage());  // 항상 킴
```

운영 환경에서는 DEBUG, INFO를 끄고 WARN, ERROR만 남길 수 있다. 근데 `e.printStackTrace()`는? **항상 출력**. 끌 방법이 없다.

### 2. 파일 로테이션 없음

!!! danger "가장 치명적인 문제"
    Logger를 쓰면 로그 파일을 **날짜별/크기별로 분리**할 수 있다.

    ```
    application-2026-03-15.log  (10MB)
    application-2026-03-14.log  (10MB)
    application-2026-03-13.log  (10MB)  ← 7일 지나면 자동 삭제
    ```

    `e.printStackTrace()`는 catalina.out **하나에 계속 쌓인다**.

    ```
    catalina.out  (4.4GB... 그리고 계속 커짐)
    ```

    이게 09장의 WAS02 사고의 직접적인 원인이다.

### 3. 포맷 없음

```
// e.printStackTrace() - 언제 발생한 건지 모름
SessionBrokenException: system.fail.session.expire
    at SecurityUtil.authorizationCheck(SecurityUtil.java:150)
    ...

// Logger - 정확한 시각, 쓰레드, 클래스 정보
2026-03-15 10:23:45.123 [exec-15] ERROR AuthenticInterceptor - ...
```

장애 분석할 때 "이 에러가 언제 발생했는지"를 모르면 분석이 안 된다. `e.printStackTrace()`는 타임스탬프가 없다.

### 4. synchronized 문제

```java
// PrintStream.println()은 synchronized다
public void println(String x) {
    synchronized (this) {  // ← 한 번에 하나의 쓰레드만
        print(x);
        newLine();
    }
}
```

`e.printStackTrace()`는 내부적으로 **synchronized** 블록을 쓴다. 여러 쓰레드가 동시에 스택 트레이스를 찍으려 하면 **줄 서서 기다린다**. 요청이 많을 때 병목이 된다.

### 5. 예외 종류 구분 불가

```java
catch(Exception e) {
    e.printStackTrace();  // SessionBrokenException이든
                          // NullPointerException이든
                          // IOException이든
                          // 전부 같은 방식으로 출력
}
```

모든 예외를 동일하게 처리한다. "세션 만료"와 "진짜 버그"를 구분할 수 없다.

---

## 영향도 계산

우리 프로젝트의 실제 수치:

| 항목 | 값 |
|------|-----|
| SessionBrokenException 발생 횟수 | **1,471회/일** |
| 스택 트레이스 1건당 줄 수 | **약 35줄** |
| 하루 불필요한 로그 라인 | **51,485줄/일** |
| 1줄 평균 크기 | 약 80바이트 |
| 하루 불필요한 로그 크기 | **약 4MB/일** |
| 468일간 누적 | **약 1.8GB** (SessionBroken만) |

!!! danger "이건 SessionBrokenException만의 수치다"
    실제로는 IOException, NullPointerException 등 다른 예외들도 `e.printStackTrace()`로 찍히고 있다. 전부 합치면 훨씬 크다.

---

## 해결: 예외별 분리 처리

```java
// 수정 전 (현재 코드)
try {
    SecurityUtil.authorizationCheckRunner(request, response);
} catch(Exception e) {
    e.printStackTrace();  // 모든 예외를 같은 방식으로
    throw e;
}
```

```java
// 수정 후
try {
    SecurityUtil.authorizationCheckRunner(request, response);
} catch(SessionBrokenException e) {
    // 세션 만료: 정상 흐름. 로그 불필요.
    throw e;
} catch(Exception e) {
    // 진짜 예외: Logger로 기록
    log.error("Authorization check failed: {}", e.getMessage());
    throw e;
}
```

!!! tip "왜 SessionBrokenException만 따로 잡나?"
    **SessionBrokenException은 정상 흐름**이기 때문이다.

    - 세션 만료 → 로그인 리다이렉트: 매일 1,471번 발생하는 일상적인 동작
    - NullPointerException: 코드 버그. 반드시 기록해야 한다.
    - IOException: 네트워크 문제. 기록할 가치가 있다.

    예외의 **성격에 따라** 처리 방식을 다르게 해야 한다. 전부 `e.printStackTrace()`로 뭉뚱그리면 진짜 문제가 묻힌다.

---

## Logger 설정 예시

```xml
<!-- log4j2.xml -->
<Appenders>
    <RollingFile name="APP_LOG"
                 fileName="logs/application.log"
                 filePattern="logs/application-%d{yyyy-MM-dd}.log">
        <PatternLayout pattern="%d{yyyy-MM-dd HH:mm:ss.SSS}
            [%t] %-5level %logger{36} - %msg%n"/>
        <Policies>
            <TimeBasedTriggeringPolicy interval="1" />
        </Policies>
        <DefaultRolloverStrategy max="30" />
    </RollingFile>
</Appenders>
```

| 설정 | 의미 |
|------|------|
| `fileName` | 현재 로그 파일 경로 |
| `filePattern` | 로테이션 시 파일 이름 패턴 (날짜별) |
| `TimeBasedTriggeringPolicy` | 매일 새 파일로 분리 |
| `DefaultRolloverStrategy max="30"` | 최대 30개 유지, 오래된 건 삭제 |

이렇게 하면 **catalina.out이 무한히 커지는 문제가 원천적으로 사라진다**.

---

## 핵심 정리

1. `e.printStackTrace()` → System.err → catalina.out (레벨/로테이션/포맷 없음)
2. Logger → 설정 파일 (레벨 제어, 일별 로테이션, 타임스탬프 포함)
3. SessionBrokenException은 정상 흐름 → 스택 트레이스 불필요
4. 진짜 예외(NPE, IOException)는 Logger로 기록
5. 예외 종류별로 catch를 분리해서 처리

---

## 확인문제

### Q1. e.printStackTrace()의 출력 대상

!!! question "문제"
    `e.printStackTrace()`가 출력하는 대상은 어디인가? Tomcat 환경에서 최종적으로 어떤 파일에 기록되나?

??? success "정답 보기"
    `e.printStackTrace()`는 **System.err**에 출력한다. Tomcat에서 System.err의 출력은 **catalina.out** 파일로 리다이렉트된다.

    System.out(표준 출력)도 catalina.out으로 간다. 결과적으로 System.out.println(), System.err.println(), e.printStackTrace() 출력이 모두 catalina.out 하나에 섞인다.

### Q2. 로그 레벨의 의미

!!! question "문제"
    다음 로그 레벨을 심각도 순서대로 나열해봐: DEBUG, ERROR, INFO, WARN

??? success "정답 보기"
    **ERROR > WARN > INFO > DEBUG** (심각한 순서)

    - **ERROR**: 즉시 대응 필요한 오류
    - **WARN**: 잠재적 문제, 주의 필요
    - **INFO**: 일반적인 운영 정보
    - **DEBUG**: 개발/디버깅용 상세 정보

    운영 환경에서는 보통 WARN 이상만 남긴다. 로그 레벨을 WARN으로 설정하면 DEBUG와 INFO는 출력되지 않는다.

### Q3. 수정 코드 이해

!!! question "문제"
    수정 코드에서 `SessionBrokenException`을 별도로 catch하는 이유를 설명해봐.
    ```java
    } catch(SessionBrokenException e) {
        throw e;  // 로그 없이 그냥 던짐
    } catch(Exception e) {
        log.error("...", e.getMessage());
        throw e;
    }
    ```

??? success "정답 보기"
    **SessionBrokenException은 세션 만료를 의미하는 정상 흐름**이기 때문이다.

    하루 1,471번 발생하는 일상적인 동작에 대해 매번 로그를 남기면 불필요한 노이즈만 늘어난다. 세션 만료는 에러가 아니라 **보안 기능의 정상 작동**이다.

    반면, `Exception` catch에 걸리는 다른 예외(NullPointerException, IOException 등)는 **진짜 문제**일 가능성이 높으므로 Logger로 기록해야 한다.

    Java의 catch는 **위에서부터 매칭**된다. SessionBrokenException은 Exception의 하위 클래스이므로, 먼저 선언해야 별도로 잡을 수 있다.

### Q4. synchronized 문제

!!! question "문제"
    `e.printStackTrace()`가 내부적으로 synchronized를 쓴다. 동시에 100개의 요청이 스택 트레이스를 찍으려 하면 어떤 현상이 발생하나?

??? success "정답 보기"
    **쓰레드 경합(contention)이 발생한다.** synchronized 블록은 한 번에 하나의 쓰레드만 진입할 수 있으므로, 나머지 99개 쓰레드는 **줄 서서 기다려야** 한다.

    이 동안 각 쓰레드가 처리 중인 요청의 응답이 지연된다. 스택 트레이스가 35줄이면 I/O도 35줄분 발생하니까, 100개 요청 x 35줄 = 3,500줄의 I/O가 직렬로 처리된다.

    Logger는 **비동기 Appender**를 쓸 수 있어서 이 문제를 회피할 수 있다.

### Q5. 파일 로테이션

!!! question "문제"
    `e.printStackTrace()`로 catalina.out에 쌓인 로그는 왜 자동으로 정리되지 않나? Logger의 로테이션은 어떻게 다른가?

??? success "정답 보기"
    `e.printStackTrace()`는 **System.err에 직접 쓰는 것**이다. Tomcat은 System.err를 catalina.out으로 리다이렉트할 뿐, 파일 관리(로테이션, 삭제)는 하지 않는다. catalina.out은 Tomcat이 재시작되거나 외부 스크립트(logrotate 등)가 처리하지 않는 한 **무한히 커진다**.

    Logger(Log4j/Logback)는 **자체적으로 로테이션을 지원**한다:
    - 날짜별 분리: 매일 새 파일 생성
    - 크기별 분리: 10MB 넘으면 새 파일
    - 보관 정책: 30일 지난 파일 자동 삭제

    이 차이가 09장 WAS02 사고의 핵심 원인이다.
