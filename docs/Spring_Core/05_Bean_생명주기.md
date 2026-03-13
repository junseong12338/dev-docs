# 05. Bean 생명주기

**이 장의 목표**: Bean이 언제 만들어지고, 언제 초기화되고, 언제 죽는지 설명할 수 있다

---

## 1. 생명주기(Lifecycle)란

```
생명주기 = 객체가 태어나서 죽을 때까지의 과정

사람:  출생 → 성장 → 활동 → 사망
Bean:  생성 → 초기화 → 사용 → 소멸

Spring이 이 전 과정을 관리한다.
new도 Spring, 초기화도 Spring, 소멸도 Spring.
```

---

## 2. Bean 생명주기 전체 흐름

!!! note "Bean 생명주기 5단계"

    **1단계: 인스턴스 생성 (new)**
    → Spring이 클래스의 생성자를 호출
    → 빈 객체가 메모리에 올라온다
    → 아직 필드는 비어있다

    **2단계: 의존성 주입 (DI)**
    → property의 value, ref를 setter로 넣어준다
    → 또는 @Resource, @Autowired로 주입
    → 이제 필드에 값이 채워진다

    **3단계: 초기화 (Initialization)**
    → afterPropertiesSet() 호출 (InitializingBean)
    → 또는 init-method 호출
    → "의존성 다 받았으니 추가 세팅 한다"

    **4단계: 사용 (Usage)**
    → 애플리케이션에서 이 Bean을 사용한다
    → 대부분의 시간을 여기서 보낸다

    **5단계: 소멸 (Destruction)**
    → 서버 종료 시 destroy() 호출
    → 또는 destroy-method 호출
    → 자원 정리 (DB 연결 닫기, 스레드 종료 등)

---

## 3. 단계별 상세

### 3.1 1단계: 인스턴스 생성

```java
// Spring이 하는 일 (내부적으로)
Object bean = clazz.newInstance();  // 리플렉션으로 생성자 호출

// 결과: 빈 객체가 만들어진다
// SqlSessionFactoryBean sqlSession = new SqlSessionFactoryBean();
// 이 시점에서 dataSource, configLocation 등은 아직 null
```

### 3.2 2단계: 의존성 주입

```java
// Spring이 XML의 property를 읽고 setter를 호출한다

// <property name="dataSource" ref="dataSource" />
sqlSession.setDataSource(dataSource);

// <property name="configLocation" value="classpath:/.../sql-mapper-config.xml" />
sqlSession.setConfigLocation(resource);

// <property name="mapperLocations" value="classpath*:/.../maria/*/*.xml" />
sqlSession.setMapperLocations(resources);

// 이제 필드가 다 채워졌다
```

### 3.3 3단계: 초기화

```
의존성이 다 주입된 후, Spring이 초기화 메서드를 호출한다.

초기화 방법 3가지:

1. InitializingBean 인터페이스의 afterPropertiesSet()
2. XML의 init-method 속성
3. @PostConstruct 어노테이션
```

```java
// 방법 1: InitializingBean (우리 프로젝트에서 사용)
public class SqlSessionFactoryBean implements InitializingBean {

    @Override
    public void afterPropertiesSet() throws Exception {
        // 의존성 주입이 끝난 후 실행된다
        // 여기서 SqlSessionFactory를 실제로 빌드한다
        this.sqlSessionFactory = buildSqlSessionFactory();
    }
}
```

```xml
<!-- 방법 2: init-method -->
<bean id="myBean" class="com.example.MyBean" init-method="init" />
```

```java
// 방법 3: @PostConstruct
public class MyBean {
    @PostConstruct
    public void init() {
        // 초기화 로직
    }
}
```

### 3.4 우리 프로젝트에서 초기화가 중요한 이유

```
RefreshableSqlSessionFactoryBean의 afterPropertiesSet():

public void afterPropertiesSet() throws Exception {
    super.afterPropertiesSet();  // 부모의 초기화 (SqlSessionFactory 빌드)
    setRefreshable();             // Timer 시작! ← 여기서 감시가 시작된다
}

이 순서:
  1단계: new RefreshableSqlSessionFactoryBean()  → 빈 객체
  2단계: setDataSource(ds), setMapperLocations(res) → 값 채움
  3단계: afterPropertiesSet() → SqlSessionFactory 빌드 + Timer 시작!
  4단계: 사용 → SQL 실행
  5단계: destroy() → Timer 종료

Timer가 3단계에서 시작되는 거다.
서버 시작하자마자 1초마다 파일 감시가 시작.
```

---

### 3.5 5단계: 소멸

```java
// DisposableBean 인터페이스의 destroy()
public class RefreshableSqlSessionFactoryBean implements DisposableBean {

    @Override
    public void destroy() throws Exception {
        timer.cancel();  // Timer 스레드 종료
    }
}
```

```
소멸은 언제 일어나나:
  → 서버 종료 (shutdown)
  → ApplicationContext.close() 호출
  → Spring이 등록된 모든 Bean의 destroy()를 호출

소멸에서 하는 일:
  → DB Connection 닫기
  → 스레드 종료 (Timer 등)
  → 파일 핸들 닫기
  → 리소스 정리

안 하면:
  → 리소스 누수 (메모리, 커넥션, 스레드 등)
```

---

## 4. 생명주기 콜백 호출 순서

!!! note "Bean 생명주기 콜백 호출 순서"

    **생성:**

    1. 생성자 호출 (new)
    2. setter 호출 (DI)
    3. @PostConstruct
    4. InitializingBean.afterPropertiesSet()
    5. init-method

    **소멸:**

    1. @PreDestroy
    2. DisposableBean.destroy()
    3. destroy-method

    3개 다 있으면 이 순서로 호출된다.
    보통은 하나만 쓴다.

---

## 5. 실전: Bean이 시작할 때 뭔가 해야 한다면

```
상황: "서버 시작할 때 캐시를 미리 로드하고 싶다"

방법 1: afterPropertiesSet()
  → InitializingBean 구현
  → Spring이 의존성 주입 후 자동 호출

방법 2: @PostConstruct
  → 메서드에 어노테이션만 붙이면 됨
  → 가장 간단

방법 3: init-method
  → XML에서 지정
  → 코드에 Spring 의존성 안 넣고 싶을 때

권장: @PostConstruct (간단, 명확)
우리 프로젝트: afterPropertiesSet() 사용 (eGovFramework 스타일)
```

---

## 6. 핵심 정리

!!! abstract "핵심 정리"

    **Bean 생명주기:**
    생성(new) → DI(setter) → 초기화 → 사용 → 소멸

    **초기화 콜백:**
    @PostConstruct / afterPropertiesSet() / init-method
    → "DI 끝났으니 추가 세팅한다"

    **소멸 콜백:**
    @PreDestroy / destroy() / destroy-method
    → "서버 꺼지니 자원 정리한다"

    **우리 프로젝트:**
    RefreshableSqlSessionFactoryBean.afterPropertiesSet()
    → SqlSessionFactory 빌드 + Timer 시작
    → destroy() → Timer 종료

    **다음 장:**
    Bean Scope
    → "같은 Bean을 달라고 하면 같은 놈이 나올까?"
