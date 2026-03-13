# 04. XML 설정 완전정복

**이 장의 목표**: Spring XML 설정 파일을 한 줄도 빠짐없이 읽을 수 있다

---

## 1. XML 설정 파일의 역할

```
XML 설정 파일 = Spring에게 보내는 "주문서"

주문서 내용:
  - 어떤 Bean을 만들어라
  - 어떤 값을 넣어라
  - 어떤 Bean끼리 연결해라
  - 어떤 패키지를 스캔해라

Spring은 서버 시작할 때 이 XML을 읽고
주문서대로 Bean을 만들고 조립한다
```

---

## 2. XML 기본 구조

### 2.1 뼈대

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
       http://www.springframework.org/schema/beans/spring-beans-3.2.xsd">

    <!-- 여기에 Bean 정의 -->

</beans>
```

```
한 줄씩:

<?xml version="1.0" encoding="UTF-8"?>
  → "이 파일은 XML이고, UTF-8 인코딩이다"
  → 모든 XML 파일의 첫 줄. 의미 없이 붙이는 거 아니다.

<beans xmlns="...">
  → 최상위 태그. "이 안에 Bean 정의가 들어간다"
  → xmlns = XML namespace. Spring 스키마를 참조한다는 뜻.

xmlns:xsi, xsi:schemaLocation
  → XML 문법 검증용 스키마 위치
  → "이 XML이 Spring 규칙에 맞는지 검증해줘"
  → 외울 필요 없다. 복붙하면 된다.
```

### 2.2 네임스페이스 종류

```
우리 프로젝트에서 쓰는 네임스페이스들:

xmlns:beans   → Bean 정의 (기본)
xmlns:context → component-scan, property-placeholder
xmlns:tx      → 트랜잭션 설정
xmlns:aop     → AOP 설정

보이면 "이 XML에서 이런 기능을 쓰겠다는 선언"이라고 이해하면 된다.
```

---

## 3. Bean 태그 완전 해부

### 3.1 기본 속성

```xml
<bean id="lobHandler"
      class="org.springframework.jdbc.support.lob.DefaultLobHandler"
      lazy-init="true" />
```

| 속성 | 의미 |
|------|------|
| id | Bean 이름 (고유 식별자) |
| class | 만들 클래스 (FQCN) |
| lazy-init | 지연 초기화 여부 |
| scope | Bean 범위 (singleton/prototype) |
| init-method | 초기화 시 호출할 메서드 |
| destroy-method | 소멸 시 호출할 메서드 |
| abstract | 추상 Bean 여부 (템플릿용) |
| parent | 부모 Bean (설정 상속) |

### 3.2 lazy-init

```
lazy-init="true":
  → 서버 시작할 때 Bean을 만들지 않는다
  → 누군가 이 Bean을 처음 요청할 때 만든다
  → "게으른 초기화"

lazy-init="false" (기본값):
  → 서버 시작할 때 바로 Bean을 만든다
  → "즉시 초기화"

예시:
  <bean id="lobHandler" class="...DefaultLobHandler" lazy-init="true" />
  → lobHandler는 누군가 쓸 때까지 안 만든다
  → LOB(Large Object) 처리가 필요한 순간에야 생성
```

---

## 4. property 태그 완전 해부

### 4.1 value - 단순 값

```xml
<property name="interval" value="1000" />
```

```
name="interval" → setInterval() 호출
value="1000"    → 인자로 "1000" 전달

Spring이 하는 일:
  bean.setInterval(1000);
  // String "1000"을 int 1000으로 자동 변환 (타입 변환)

타입 변환 규칙:
  value="1000"    → int, long, float 등으로 자동 변환
  value="true"    → boolean true로 변환
  value="hello"   → String "hello"
  value="classpath:/..." → Resource 객체로 변환 (Spring 특수)
```

### 4.2 ref - Bean 참조

```xml
<property name="dataSource" ref="dataSource" />
```

```
name="dataSource" → setDataSource() 호출
ref="dataSource"  → 컨테이너에서 id="dataSource"인 Bean을 찾아서 전달

Spring이 하는 일:
  Object ds = container.getBean("dataSource");  // Bean 찾기
  bean.setDataSource(ds);                       // 주입
```

### 4.3 classpath: vs classpath*:

```
value="classpath:/egovframework/sqlmap/sql-mapper-config.xml"
  → classpath: (콜론 뒤에 * 없음)
  → 클래스패스에서 정확히 이 경로의 파일 1개를 찾는다

value="classpath*:/egovframework/sqlmap/maria/*/*.xml"
  → classpath*: (별표 있음)
  → 모든 클래스패스에서 이 패턴에 맞는 파일 전부 찾는다
  → JAR 안에 있는 것도 찾는다

차이:
  classpath:  → 1개만 찾는다 (처음 발견한 것)
  classpath*: → 전부 찾는다 (여러 개 가능)
```

### 4.4 ${...} - 프로퍼티 치환

```xml
<property name="mapperLocations"
          value="classpath*:/egovframework/sqlmap/${framework.database.db_type}/*/*.xml" />
```

```
${framework.database.db_type} = 프로퍼티 파일에서 값을 가져온다

프로퍼티 파일 (예: globals.properties):
  framework.database.db_type=maria

치환 결과:
  classpath*:/egovframework/sqlmap/maria/*/*.xml

왜 이렇게 하느냐:
  → DB 종류 바꿀 때 코드 수정 없이 프로퍼티 파일만 수정
  → maria → oracle로 바꾸면 SQL 매퍼 경로가 자동으로 바뀐다
```

---

## 5. 우리 프로젝트 XML 완전 해석

### 5.1 context-sqlMap.xml (현재 상태)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://www.springframework.org/schema/beans
       http://www.springframework.org/schema/beans/spring-beans-3.2.xsd">

    <!-- lob Handler -->
    <bean id="lobHandler"
          class="org.springframework.jdbc.support.lob.DefaultLobHandler"
          lazy-init="true" />

    <!-- SqlSession setup for MyBatis Database Layer -->
    <bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean">
        <property name="dataSource" ref="dataSource" />
        <property name="configLocation"
                  value="classpath:/egovframework/sqlmap/sql-mapper-config.xml" />
        <property name="mapperLocations"
                  value="classpath*:/egovframework/sqlmap/${framework.database.db_type}/*/*.xml" />
    </bean>

    <bean class="egovframework.rte.psl.dataaccess.mapper.MapperConfigurer">
        <property name="basePackage"
                  value="egovframework.mediopia.lxp.**.service.impl" />
        <property name="sqlSessionFactoryBeanName" value="sqlSession"/>
    </bean>

</beans>
```

### 5.2 한 줄씩 완전 해석

```
[1~4줄] XML 선언 + Spring beans 네임스페이스
  → "이 파일은 Spring Bean 설정 파일이다"

[6~8줄] lobHandler Bean
  <bean id="lobHandler" class="...DefaultLobHandler" lazy-init="true" />
  → Bean 이름: lobHandler
  → 클래스: DefaultLobHandler (LOB 데이터 처리용)
  → lazy-init="true": 쓸 때까지 안 만든다
  → 용도: BLOB/CLOB 같은 대용량 데이터 처리

[10~15줄] sqlSession Bean
  <bean id="sqlSession" class="org.mybatis.spring.SqlSessionFactoryBean">
  → Bean 이름: sqlSession
  → 클래스: SqlSessionFactoryBean (MyBatis 공식)
  → 용도: SQL 실행을 위한 세션 팩토리

  <property name="dataSource" ref="dataSource" />
  → setDataSource(dataSource Bean) 호출
  → DB 연결 정보를 가진 dataSource Bean을 주입
  → dataSource Bean은 다른 XML에서 정의되어 있다

  <property name="configLocation" value="classpath:/.../sql-mapper-config.xml" />
  → setConfigLocation() 호출
  → MyBatis 설정 파일 경로 지정

  <property name="mapperLocations" value="classpath*:/.../maria/*/*.xml" />
  → setMapperLocations() 호출
  → SQL 매퍼 XML 파일들 경로 (126개)

[17~20줄] MapperConfigurer Bean
  <bean class="...MapperConfigurer">
  → id 없음! class만 있다
  → id 없는 Bean = 다른 데서 참조 안 하는 Bean
  → Spring이 자동으로 이름을 붙인다

  <property name="basePackage" value="...**.service.impl" />
  → 이 패키지 하위의 Mapper 인터페이스를 자동 스캔
  → ** = 모든 하위 패키지

  <property name="sqlSessionFactoryBeanName" value="sqlSession"/>
  → "sqlSession"이라는 Bean을 SqlSessionFactory로 사용해라
  → 주의: ref가 아니라 value! Bean 이름을 문자열로 전달
```

---

## 6. 여러 XML 파일의 관계

### 6.1 설정 파일 분리

```
Spring은 하나의 XML에 다 넣지 않는다.
역할별로 분리한다:

context-common.xml      → 공통 설정 (component-scan 등)
context-datasource.xml  → DataSource (DB 연결 정보)
context-sqlMap.xml      → MyBatis 설정
context-transaction.xml → 트랜잭션 설정
context-aspect.xml      → AOP 설정

이 파일들을 Spring이 전부 읽어서 하나의 컨테이너로 합친다.

그래서:
  context-sqlMap.xml에서 ref="dataSource"라고 하면
  context-datasource.xml에 정의된 dataSource Bean을 찾는다.
  → 파일은 다르지만 같은 컨테이너 안이니까 가능
```

### 6.2 파일 간 참조 흐름

```
context-datasource.xml:
  <bean id="dataSource" class="BasicDataSource">  ← 여기서 정의

context-sqlMap.xml:
  <bean id="sqlSession" class="SqlSessionFactoryBean">
    <property name="dataSource" ref="dataSource" />  ← 여기서 참조
  </bean>

context-transaction.xml:
  <bean id="txManager" class="DataSourceTransactionManager">
    <property name="dataSource" ref="dataSource" />  ← 여기서도 참조
  </bean>

→ dataSource Bean 하나를 여러 곳에서 공유
→ DI의 핵심: 한 번 만들고, 필요한 곳에 주입
```

---

## 7. 자주 보는 XML 패턴

### 7.1 component-scan

```xml
<context:component-scan base-package="egovframework.mediopia.lxp" />
```

```
의미:
  "이 패키지 하위에서 @Component, @Service, @Repository, @Controller
   어노테이션이 붙은 클래스를 자동으로 Bean으로 등록해라"

→ XML에 하나하나 <bean> 안 써도 된다
→ 어노테이션만 붙이면 자동 등록
→ 07장에서 자세히 다룬다
```

### 7.2 property-placeholder

```xml
<context:property-placeholder
    location="classpath:/egovframework/egovProps/globals.properties" />
```

```
의미:
  "globals.properties 파일을 읽어서
   ${...} 패턴을 치환해라"

globals.properties:
  framework.database.db_type=maria
  db.url=jdbc:mariadb://...

XML에서:
  value="${framework.database.db_type}" → "maria"로 치환
  value="${db.url}" → "jdbc:mariadb://..."로 치환
```

### 7.3 import

```xml
<import resource="classpath:/egovframework/spring/context-datasource.xml" />
```

```
의미:
  "다른 XML 파일을 불러와서 합쳐라"
  → 분리된 설정 파일을 하나로 합칠 때 사용
```

---

## 8. 핵심 정리

!!! abstract "핵심 정리"

    **XML 설정** = Spring에게 보내는 주문서

    `<bean id="" class="">`:
    → "이 클래스의 객체를 이 이름으로 만들어라"

    `<property name="" value="">`:
    → setter로 단순 값 넣기

    `<property name="" ref="">`:
    → setter로 다른 Bean 넣기 (DI)

    **classpath: vs classpath*:**
    → 1개 vs 전부

    **${...}:**
    → properties 파일에서 값 치환

    **파일 분리:**
    → 역할별로 XML 분리, 같은 컨테이너에서 합쳐진다

    **다음 장:**
    Bean 생명주기
    → Bean이 태어나고, 초기화되고, 사용되고, 죽는 과정
