# 01. Spring이 뭐야

**이 장의 목표**: "Spring이 뭐야?"라는 질문에 정확히 대답할 수 있다

---

## 1. 먼저, 프레임워크가 뭐야

### 1.1 라이브러리 vs 프레임워크

```
라이브러리 (Library):
  → 내가 필요할 때 가져다 쓰는 도구
  → 내가 호출한다
  → 예: StringUtils.isEmpty("hello") → 내가 직접 호출

프레임워크 (Framework):
  → 틀(뼈대)을 제공하고, 내 코드를 프레임워크가 호출한다
  → 프레임워크가 나를 호출한다
  → 예: Spring이 내 Controller를 호출한다
```

### 1.2 비유

```
라이브러리 = 공구 세트
  → 내가 망치 들고 못을 박는다
  → 내가 주체

프레임워크 = 공장 컨베이어 벨트
  → 벨트가 돌아가고, 내가 맡은 공정에서 작업한다
  → 벨트(프레임워크)가 주체, 나는 한 파트 담당

Spring = 자바 웹 애플리케이션의 컨베이어 벨트
```

### 1.3 핵심 차이: "누가 누구를 호출하느냐"

!!! note "핵심 차이"

    라이브러리: 내 코드 --호출--> 라이브러리 코드

    프레임워크: 프레임워크 --호출--> 내 코드

    이 차이를 **"제어의 역전(IoC)"**이라고 한다.

---

## 2. IoC (Inversion of Control) - 제어의 역전

### 2.1 "제어"가 뭔데

```
제어 = 프로그램의 흐름을 결정하는 것

일반적인 프로그래밍:
  1. main() 시작
  2. 내가 객체를 만든다 (new)
  3. 내가 메서드를 호출한다
  4. 내가 흐름을 제어한다

→ 제어권이 "나"한테 있다
```

### 2.2 "역전"이 뭔데

```
Spring을 쓰면:
  1. Spring이 시작된다
  2. Spring이 객체를 만든다
  3. Spring이 내 코드를 호출한다
  4. Spring이 흐름을 제어한다

→ 제어권이 "Spring"한테 넘어갔다
→ 제어가 역전(Inversion)됐다
→ 이게 IoC (Inversion of Control)
```

### 2.3 코드로 보면

```java
// IoC 없이 (내가 다 한다)
public class OrderService {
    private OrderRepository repository = new OrderRepository();  // 내가 직접 생성

    public void createOrder() {
        repository.save(order);  // 내가 직접 호출
    }
}

// IoC 적용 (Spring이 해준다)
public class OrderService {
    private OrderRepository repository;  // 선언만 한다

    // Spring이 repository를 만들어서 넣어준다 (주입)
    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }

    public void createOrder() {
        repository.save(order);
    }
}
```

### 2.4 왜 이렇게 하는 건데

```
Q: "내가 직접 new 하면 안 돼? 왜 굳이 Spring한테 맡겨?"

A: 직접 new 하면 생기는 문제:

  1. 결합도가 높아진다
     → OrderService가 OrderRepository를 직접 알고 있다
     → OrderRepository 바꾸려면 OrderService도 수정해야 한다

  2. 테스트가 어렵다
     → new OrderRepository()가 하드코딩되어 있으면
     → 가짜(Mock) 객체로 바꿀 수가 없다

  3. 객체 관리가 분산된다
     → 여기저기서 new 하면 같은 객체가 여러 개 생긴다
     → 메모리 낭비, 상태 관리 혼란

Spring한테 맡기면:
  → Spring이 객체를 한 곳에서 관리한다
  → 바꿔야 할 때 설정만 바꾸면 된다
  → 테스트할 때 가짜 객체를 쉽게 주입한다
```

---

## 3. Spring의 정체

### 3.1 한 문장 정의

```
Spring = Java 애플리케이션을 위한 IoC 컨테이너 기반 프레임워크

풀어서 말하면:
  "객체의 생성, 관리, 주입을 대신 해주는 틀"
```

### 3.2 Spring이 하는 일

!!! note "Spring이 하는 3가지"

    **1. 객체를 만든다 (Bean 생성)**
    : new 대신 Spring이 객체를 생성
    : XML이나 어노테이션으로 "이거 만들어" 지시

    **2. 객체를 관리한다 (Bean 관리)**
    : 만든 객체를 컨테이너에 보관
    : 생명주기 관리 (생성 → 초기화 → 사용 → 소멸)

    **3. 객체를 연결한다 (의존성 주입, DI)**
    : A가 B를 필요로 하면, Spring이 B를 A에 넣어준다
    : "너 이거 필요하지? 여기 있어" 해주는 것

### 3.3 Spring 컨테이너

```
컨테이너 = Bean(객체)들이 살고 있는 공간

비유:
  컨테이너 = 아파트 관리사무소
  Bean = 아파트 주민(객체)

  관리사무소가 하는 일:
    - 주민 입주 (Bean 생성)
    - 주민 관리 (Bean 관리)
    - 주민끼리 연결 (DI: "302호에 택배 왔어요")
    - 주민 퇴거 (Bean 소멸)

  내가 하는 일:
    - "302호에 누구 살게 해줘" (Bean 등록 요청)
    - "302호 주민 좀 불러줘" (Bean 조회)
```

---

## 4. Spring의 구성

### 4.1 Spring Framework 모듈

!!! note "Spring Framework"

    **Core Container (핵심)**

    - `spring-core` : 기본 유틸리티
    - `spring-beans` : Bean 생성/관리
    - `spring-context` : ApplicationContext
    - `spring-expression` : SpEL (표현식 언어)

    **Web**

    - `spring-web` : 웹 기본
    - `spring-webmvc` : MVC 패턴 (Controller 등)

    **Data Access**

    - `spring-jdbc` : DB 연결
    - `spring-tx` : 트랜잭션 관리

    **AOP**

    - `spring-aop` : 관점 지향 프로그래밍

    이 커리큘럼에서 집중하는 것: **Core Container**
    → Bean, DI, Context = Spring의 심장

---

## 5. Spring 없이 vs Spring 있을 때

### 5.1 Spring 없이

```java
// 내가 직접 다 한다
public class App {
    public static void main(String[] args) {
        // 1. 내가 직접 객체 생성
        DataSource dataSource = new BasicDataSource();
        dataSource.setUrl("jdbc:mariadb://...");
        dataSource.setUsername("root");

        // 2. 내가 직접 의존성 연결
        SqlSessionFactory sqlSession = new SqlSessionFactoryBean();
        sqlSession.setDataSource(dataSource);  // 내가 직접 넣는다

        // 3. 내가 직접 서비스 생성
        UserService userService = new UserServiceImpl();
        userService.setSqlSession(sqlSession);  // 내가 직접 넣는다

        // 객체가 10개, 20개, 100개 되면?
        // → 내가 다 관리해야 한다
        // → 지옥
    }
}
```

### 5.2 Spring 있을 때

```xml
<!-- Spring한테 지시한다 (XML 설정) -->

<!-- "dataSource라는 이름으로 BasicDataSource 객체 만들어" -->
<bean id="dataSource" class="org.apache.commons.dbcp2.BasicDataSource">
    <property name="url" value="jdbc:mariadb://..." />
    <property name="username" value="root" />
</bean>

<!-- "sqlSession이라는 이름으로 SqlSessionFactoryBean 만들고,
     dataSource를 넣어줘" -->
<bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean">
    <property name="dataSource" ref="dataSource" />
</bean>
```

```java
// 내 코드에서는 그냥 가져다 쓴다
public class UserServiceImpl {
    @Resource(name = "sqlSession")  // "sqlSession 좀 줘"
    private SqlSession sqlSession;

    // Spring이 알아서 sqlSession을 넣어준다
    // 내가 new 안 한다
}
```

### 5.3 차이 정리

| Spring 없이 | Spring 있을 때 |
|-------------|---------------|
| 내가 new 한다 | Spring이 new 한다 |
| 내가 연결한다 | Spring이 연결(주입)한다 |
| 내가 관리한다 | Spring이 관리한다 |
| 객체 많으면 지옥 | XML/어노테이션으로 선언만 |
| 바꾸려면 코드 수정 | 설정만 바꾸면 됨 |
| 테스트 어려움 | Mock 주입 쉬움 |

---

## 6. Spring Boot vs Spring Framework

```
혼동하기 쉬운 것:

Spring Framework:
  → 원조. XML 설정 많이 쓴다.
  → 우리 프로젝트가 이것. (eGovFramework 기반)
  → 설정 직접 다 해야 한다.

Spring Boot:
  → Spring Framework를 편하게 쓰게 만든 것.
  → 자동 설정 (Auto Configuration)
  → XML 거의 안 쓴다.
  → 최신 프로젝트는 대부분 이것.

관계:
  Spring Boot ⊃ Spring Framework
  (Boot가 Framework를 포함하고 편의기능을 추가한 것)

우리 프로젝트:
  → Spring Framework + eGovFramework
  → XML 설정 방식
  → 이 커리큘럼이 이것을 다루는 이유
```

---

## 7. 핵심 정리

!!! abstract "핵심 정리"

    **Spring** = IoC 컨테이너 기반 프레임워크

    **IoC (제어의 역전):**
    내가 제어하던 것을 Spring이 제어한다
    → 객체 생성, 관리, 연결을 Spring이 대신 한다

    **프레임워크 vs 라이브러리:**
    라이브러리: 내가 호출한다
    프레임워크: 프레임워크가 나를 호출한다

    **Spring이 하는 3가지:**

    1. 객체를 만든다 (Bean 생성)
    2. 객체를 관리한다 (Bean 관리)
    3. 객체를 연결한다 (DI, 의존성 주입)

    **다음 장:**
    Bean이 뭐야
    → Spring이 만들고 관리하는 "객체"의 정체
