# 06. Bean Scope

**이 장의 목표**: singleton과 prototype의 차이를 정확히 설명할 수 있다

---

## 1. Scope란

```
Scope = Bean의 생존 범위
      = "같은 Bean을 달라고 하면 같은 놈이 나오냐, 새 놈이 나오냐"

두 가지만 알면 된다:
  1. singleton (기본값)
  2. prototype
```

---

## 2. Singleton (기본값)

### 2.1 정의

```
singleton = 컨테이너 당 1개만 생성
          = 누가 요청하든 항상 같은 객체가 나온다

Spring Bean의 기본 Scope가 singleton이다.
scope를 따로 지정하지 않으면 전부 singleton.
```

### 2.2 동작

```java
// 어디서 가져와도 같은 객체
@Resource(name = "sqlSession")
private SqlSession sqlSession;  // → 주소: 0x001

// 다른 Service에서도
@Resource(name = "sqlSession")
private SqlSession sqlSession;  // → 주소: 0x001 (같은 객체!)

// sqlSession Bean은 1개만 존재
// 100개의 Service가 가져가도 전부 같은 객체
```

### 2.3 비유

```
싱글톤 = 학교의 교장실

교장실은 학교에 1개다.
1학년이 가도, 3학년이 가도 같은 교장실.
"교장실 어디에요?" → 항상 같은 곳을 안내한다.

Bean도 마찬가지:
"sqlSession 줘" → 항상 같은 객체를 준다.
```

### 2.4 왜 기본이 singleton인가

```
이유:

1. 메모리 절약
   → 같은 객체를 100번 만들 이유가 없다
   → 1개 만들고 공유하면 된다

2. 성능
   → 객체 생성 비용이 없다 (이미 만들어져 있으니까)
   → 특히 DB Connection, SqlSession 같은 무거운 객체

3. 상태 관리
   → 1개 객체를 관리하면 되니까 단순

우리 프로젝트:
  dataSource: singleton → DB Connection Pool 1개 공유
  sqlSession: singleton → MyBatis 세션 팩토리 1개 공유
  Service들: singleton → 상태 없는 비즈니스 로직
```

### 2.5 singleton 주의점

!!! warning "singleton 주의사항"

    **1. 상태를 가지면 위험하다**

    ```java
    // 위험한 코드
    @Service
    public class UserService {
        private User currentUser;  // 상태! 위험!

        public void login(User user) {
            this.currentUser = user;  // A가 로그인
        }
        public User getUser() {
            return this.currentUser;  // B가 요청하면
        }
        // → B한테 A의 정보가 나간다!
        // → singleton은 공유 객체이므로 상태 X
    }
    ```

    **2. 해결: Bean에 상태를 넣지 않는다**
    → Service, Repository는 상태 없이 메서드만
    → 상태가 필요하면 메서드 파라미터로 받는다
    → 또는 ThreadLocal 사용

---

## 3. Prototype

### 3.1 정의

```
prototype = 요청할 때마다 새 객체를 생성
          = 매번 new

요청 1: sqlSession 줘 → 새 객체 (0x001)
요청 2: sqlSession 줘 → 새 객체 (0x002)
요청 3: sqlSession 줘 → 새 객체 (0x003)
```

### 3.2 설정

```xml
<!-- singleton (기본값, 생략 가능) -->
<bean id="userService" class="...UserServiceImpl" scope="singleton" />

<!-- prototype -->
<bean id="command" class="...Command" scope="prototype" />
```

### 3.3 언제 쓰느냐

```
prototype을 쓰는 경우:
  → Bean이 상태를 가져야 할 때
  → 매번 새로운 객체가 필요할 때
  → 예: Command 객체, DTO 생성 등

실무에서는 거의 안 쓴다:
  → 대부분의 Bean은 상태가 없으므로 singleton으로 충분
  → prototype이 필요한 상황 자체가 드물다
  → 우리 프로젝트에서도 전부 singleton (기본값)
```

---

## 4. Singleton vs Prototype 비교

| Singleton | Prototype |
|-----------|-----------|
| 컨테이너당 1개 | 요청마다 새로 생성 |
| 기본값 | scope="prototype" 명시 필요 |
| Spring이 소멸 관리 | Spring이 소멸 관리 안 함 |
| 상태 가지면 위험 | 상태 가져도 안전 |
| 메모리 효율적 | 메모리 더 사용 |
| 99% 이것을 쓴다 | 거의 안 쓴다 |

!!! warning "주의"

    prototype은 Spring이 destroy()를 호출 안 한다!
    → 생성만 해주고 이후 관리는 안 한다
    → 자원 정리가 필요하면 직접 해야 한다

---

## 5. 웹 전용 Scope (참고)

```
Spring Web에서 추가로 제공하는 Scope:

  request:   HTTP 요청 하나당 1개
  session:   HTTP 세션 하나당 1개
  application: ServletContext당 1개

우리 프로젝트에서는 거의 안 쓴다.
알아만 두면 된다.
```

---

## 6. 우리 프로젝트에서 Scope

```
context-sqlMap.xml:
  <bean id="lobHandler" ...>     → singleton (기본값)
  <bean id="sqlSession" ...>     → singleton (기본값)
  <bean class="MapperConfigurer"> → singleton (기본값)

전부 singleton이다.
scope를 지정 안 했으니까 전부 기본값 = singleton.

이게 정상이다.
Service, Repository, DataSource, SqlSession 등
서버에서 1개면 충분한 것들은 전부 singleton.
```

---

## 7. 핵심 정리

!!! abstract "핵심 정리"

    **Scope** = Bean의 생존 범위

    **singleton (기본값):**
    → 컨테이너당 1개. 항상 같은 객체 반환.
    → 99% 이것. 상태 넣지 말 것.

    **prototype:**
    → 요청마다 새 객체. 거의 안 쓴다.
    → Spring이 소멸 관리 안 함.

    **singleton 주의:** 상태(필드에 값 저장) 금지
    → 공유 객체니까 다른 사용자 데이터가 섞일 수 있다

    **다음 장:**
    어노테이션 설정
    → XML 대신 @Component, @Service로 Bean 등록
