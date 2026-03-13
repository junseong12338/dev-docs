# 02. Bean이 뭐야

**이 장의 목표**: "Bean이 뭐야?"에 정확히 대답하고, XML에서 Bean 등록하는 걸 읽을 수 있다

---

## 1. Bean의 정의

### 1.1 한 문장 정의

```
Bean = Spring 컨테이너가 생성하고 관리하는 객체

그냥 "객체"야. 특별한 게 아니다.
다만 "Spring이 관리하는" 객체라는 점이 다르다.
```

### 1.2 일반 객체 vs Bean

```java
// 일반 객체 - 내가 직접 만든다
UserService service = new UserService();
// → 이건 Bean이 아니다
// → 내가 만들었고, 내가 관리한다

// Bean - Spring이 만든다
// XML에 이렇게 선언하면:
// <bean id="userService" class="com.example.UserService" />
// → Spring이 UserService 객체를 만든다
// → Spring이 관리한다
// → 이게 Bean이다
```

### 1.3 핵심 차이

!!! note "일반 객체 vs Bean"

    **일반 객체:**

    - 내가 new로 만든다
    - 내가 사용한다
    - GC가 알아서 정리한다
    - 누가 이 객체를 쓰는지 아무도 모른다

    **Bean:**

    - Spring이 만든다
    - Spring이 이름(id)을 붙여서 관리한다
    - Spring이 생명주기를 관리한다 (생성→초기화→사용→소멸)
    - 누가 이 Bean을 쓰는지 Spring이 안다
    - 필요한 곳에 Spring이 넣어준다 (DI)

---

## 2. Bean 등록 방법

### 2.1 XML로 등록 (우리 프로젝트 방식)

```xml
<!-- 가장 기본적인 Bean 등록 -->
<bean id="userService" class="com.example.service.UserService" />
```

```
해석:
  <bean          → "Bean을 등록하겠다"
  id="userService"   → "이름은 userService로"
  class="com.example.service.UserService"  → "이 클래스의 객체를"
  />             → "끝"

Spring이 하는 일:
  UserService userService = new UserService();
  컨테이너에 "userService"라는 이름으로 저장
```

### 2.2 id란

```
id = Bean의 고유 이름
  → 컨테이너에서 이 Bean을 찾을 때 쓰는 식별자
  → 중복 불가

비유:
  아파트 호수와 같다
  "302호 주민 불러주세요" = "userService Bean 가져와"

예시:
  <bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean" />
  → "sqlSession"이라는 이름으로 SqlSessionFactoryBean 객체를 등록
```

### 2.3 class란

```
class = 어떤 클래스의 객체를 만들 건지
  → 패키지명 포함 전체 경로 (FQCN: Fully Qualified Class Name)

예시:
  class="org.mybatis.spring.SqlSessionFactoryBean"

  패키지: org.mybatis.spring
  클래스: SqlSessionFactoryBean

  Spring은 이걸 보고:
  → 이 클래스를 찾아서
  → new SqlSessionFactoryBean() 을 실행한다
```

---

## 3. Bean에 값 넣기 (property)

### 3.1 value - 단순 값 넣기

```xml
<bean id="dataSource" class="org.apache.commons.dbcp2.BasicDataSource">
    <property name="url" value="jdbc:mariadb://localhost:3306/mydb" />
    <property name="username" value="root" />
    <property name="password" value="1234" />
</bean>
```

```
해석:
  <property          → "이 Bean의 필드에 값을 넣겠다"
  name="url"         → "url이라는 필드에"
  value="jdbc:..."   → "이 문자열 값을"
  />

Spring이 하는 일:
  BasicDataSource dataSource = new BasicDataSource();
  dataSource.setUrl("jdbc:mariadb://localhost:3306/mydb");
  dataSource.setUsername("root");
  dataSource.setPassword("1234");

핵심:
  name="url" → setUrl() 메서드를 호출한다
  name="username" → setUsername() 메서드를 호출한다
  → property의 name은 setter 메서드 이름과 매핑된다
```

### 3.2 ref - 다른 Bean 참조

```xml
<bean id="dataSource" class="org.apache.commons.dbcp2.BasicDataSource">
    <property name="url" value="jdbc:mariadb://..." />
</bean>

<bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean">
    <property name="dataSource" ref="dataSource" />
</bean>
```

```
해석:
  <property name="dataSource" ref="dataSource" />

  name="dataSource"  → "이 Bean의 dataSource 필드에"
  ref="dataSource"   → "dataSource라는 이름의 다른 Bean을 넣어라"

  value vs ref:
    value = 문자열, 숫자 등 단순 값
    ref   = 다른 Bean 객체를 참조

Spring이 하는 일:
  // 먼저 dataSource Bean을 만든다
  BasicDataSource dataSource = new BasicDataSource();
  dataSource.setUrl("jdbc:mariadb://...");

  // 그 다음 sqlSession Bean을 만들고, dataSource를 넣어준다
  SqlSessionFactoryBean sqlSession = new SqlSessionFactoryBean();
  sqlSession.setDataSource(dataSource);  // ref="dataSource" → 이 줄

이게 바로 DI(의존성 주입)다.
sqlSession이 dataSource를 "필요"로 하는데,
Spring이 "알아서 넣어준" 것.
```

### 3.3 value vs ref 정리

!!! tip "value vs ref"

    **value:**
    → 문자열, 숫자, boolean 등 단순 값
    → `value="1000"`
    → `value="jdbc:mariadb://..."`
    → `value="true"`

    **ref:**
    → 다른 Bean 객체를 참조
    → `ref="dataSource"` → dataSource라는 id의 Bean을 넣어라
    → `ref="sqlSession"` → sqlSession이라는 id의 Bean을 넣어라

    **헷갈리면:**
    "넣을 게 글자/숫자야?" → value
    "넣을 게 다른 객체야?" → ref

---

## 4. 우리 프로젝트에서 Bean 읽기

### 4.1 context-sqlMap.xml

```xml
<bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean">
    <property name="dataSource" ref="dataSource" />
    <property name="configLocation"
              value="classpath:/egovframework/sqlmap/sql-mapper-config.xml" />
    <property name="mapperLocations"
              value="classpath*:/egovframework/sqlmap/${framework.database.db_type}/*/*.xml" />
</bean>
```

```
한 줄씩 해석:

1. <bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean">
   → "sqlSession"이라는 이름으로 SqlSessionFactoryBean 객체를 만들어라

2. <property name="dataSource" ref="dataSource" />
   → dataSource 필드에 "dataSource"라는 Bean을 넣어라 (ref = 다른 Bean)

3. <property name="configLocation" value="classpath:/.../sql-mapper-config.xml" />
   → configLocation 필드에 이 경로 문자열을 넣어라 (value = 문자열)

4. <property name="mapperLocations" value="classpath*:/.../maria/*/*.xml" />
   → mapperLocations 필드에 이 경로 패턴을 넣어라 (value = 문자열)
   → classpath*: → 모든 classpath에서 찾겠다
   → */*.xml → 하위폴더/아무이름.xml

Spring이 실제로 하는 것:
  SqlSessionFactoryBean sqlSession = new SqlSessionFactoryBean();
  sqlSession.setDataSource(dataSource);                    // ref
  sqlSession.setConfigLocation("classpath:/.../..xml");    // value
  sqlSession.setMapperLocations("classpath*:/.../..xml");  // value
```

---

## 5. Bean 등록 = 설계도 제출

```
Bean 등록은 "이렇게 만들어줘"라는 설계도를 Spring에 제출하는 것이다.

<bean id="sqlSession" class="SqlSessionFactoryBean">
    <property name="dataSource" ref="dataSource" />
</bean>

이 XML은 코드가 아니다.
이건 Spring에게 보내는 "주문서"다.

주문서 내용:
  - 이름: sqlSession
  - 종류: SqlSessionFactoryBean
  - 재료: dataSource라는 Bean을 넣어줘

Spring이 이 주문서를 읽고:
  1. SqlSessionFactoryBean 클래스를 찾는다
  2. new SqlSessionFactoryBean()으로 객체를 만든다
  3. dataSource Bean을 찾아서 setDataSource()로 넣어준다
  4. 컨테이너에 "sqlSession"이라는 이름으로 보관한다
  5. 누군가 "sqlSession 줘" 하면 이걸 꺼내준다
```

---

## 6. Spring 컨테이너 내부

### 6.1 컨테이너 = Bean 저장소

!!! note "Spring 컨테이너"

    | 이름(id) | 객체(Bean) |
    |----------|-----------|
    | "dataSource" | BasicDataSource 객체 |
    | "sqlSession" | SqlSessionFactoryBean 객체 |
    | "userService" | UserServiceImpl 객체 |
    | "lobHandler" | DefaultLobHandler 객체 |
    | ... | ... |

    = 이름(key) → 객체(value)의 Map과 비슷하다
    = 내부적으로 `Map<String, Object>` 같은 구조

### 6.2 Bean을 가져오는 방법

```java
// 방법 1: 이름으로 가져오기
ApplicationContext context = ...;
UserService service = (UserService) context.getBean("userService");

// 방법 2: 타입으로 가져오기
UserService service = context.getBean(UserService.class);

// 방법 3: 어노테이션으로 주입받기 (가장 일반적)
@Resource(name = "userService")
private UserService userService;
// → Spring이 컨테이너에서 "userService" Bean을 찾아서 넣어준다
```

---

## 7. 자주 하는 실수

### 7.1 Bean 등록 안 하고 쓰기

```java
// Bean 등록 안 한 클래스를 @Resource로 주입받으면
@Resource
private MyNewService myNewService;  // → 에러! Bean이 없다!

// 에러 메시지:
// No qualifying bean of type 'MyNewService'
// = "MyNewService라는 Bean이 컨테이너에 없다"

// 해결: XML에 등록하거나, @Component 어노테이션 붙이기
```

### 7.2 id 오타

```xml
<bean id="dataSoruce" class="...BasicDataSource" />
<!--        ↑ 오타! dataSource가 아니라 dataSoruce -->

<bean id="sqlSession" class="...SqlSessionFactoryBean">
    <property name="dataSource" ref="dataSource" />
    <!--                              ↑ "dataSource" Bean을 찾는데 없음! -->
    <!-- "dataSoruce"는 있지만 "dataSource"는 없어서 에러 -->
</bean>

// 에러: No bean named 'dataSource' available
```

---

## 8. 핵심 정리

!!! abstract "핵심 정리"

    **Bean** = Spring 컨테이너가 생성하고 관리하는 객체

    **Bean 등록 (XML):**
    ```xml
    <bean id="이름" class="클래스">
        <property name="필드" value="값" />
        <property name="필드" ref="다른Bean이름" />
    </bean>
    ```

    - `id` = Bean의 이름 (고유 식별자)
    - `class` = 만들 클래스 (FQCN)
    - `property name` = setter 메서드와 매핑
    - `value` = 문자열/숫자 값
    - `ref` = 다른 Bean 참조

    **Spring 컨테이너** = Bean들의 저장소 = `Map<이름, 객체>` 같은 구조

    **다음 장:**
    DI (의존성 주입)
    → "왜 ref로 다른 Bean을 넣는 건지" 깊이 파고든다
