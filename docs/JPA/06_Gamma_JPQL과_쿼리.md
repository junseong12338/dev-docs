# 06. JPQL과 @Query - Gamma

---

## 1. 이게 뭐야? — "엔티티 대상 SQL"

findByHostStatus() 같은 쿼리 메서드로 안 되는 복잡한 쿼리? **@Query**로 직접 써.

근데 SQL이 아니야. **JPQL(Java Persistence Query Language)**이라는 걸 써. SQL이랑 비슷한데, 테이블이 아니라 **엔티티 클래스**를 대상으로 쿼리한다는 차이가 있어.

```
SQL:   SELECT * FROM TB_NEXCLASS_TERM WHERE TERM_CD = '2026-1'
JPQL:  SELECT t FROM Term t WHERE t.termCd = '2026-1'
            ^^^^      ^^^            ^^^^^^^^
            엔티티명   별칭           필드명 (컬럼명 아님!)
```

---

## 2. 어떻게 돌아가?

```
쿼리 메서드    →  간단한 WHERE 조건 (findByXxx)
@Query JPQL   →  복잡한 조건, JOIN, 집계
@Query native →  진짜 SQL (최후의 수단)
```

단순한 거 → 쿼리 메서드.
좀 복잡한 거 → @Query JPQL.
JPQL로 안 되는 거 → 네이티브 쿼리.

---

## 3. 코드로 보자

### 3.1 @Query JPQL — NexClass 실전

```java
@Repository
public interface HostAssignmentRepository extends JpaRepository<HostAssignment, Long> {

    @Query("SELECT a.hostEmail FROM HostAssignment a " +
           "WHERE a.startTime < :endTime AND a.endTime > :startTime")
    List<String> findAssignedHostEmails(
        @Param("startTime") LocalDateTime startTime,
        @Param("endTime") LocalDateTime endTime
    );
}
```

- `HostAssignment` — 테이블명 아니고 엔티티 클래스명
- `a.hostEmail` — 컬럼명 아니고 자바 필드명
- `:startTime` — 파라미터 바인딩
- `@Param("startTime")` — 파라미터명 연결

### MyBatis 비교

```xml
<select id="findAssignedHostEmails" resultType="String">
    SELECT HOST_EMAIL
    FROM TB_NEXCLASS_HOST_ASSIGNMENT
    WHERE START_TIME < #{endTime} AND END_TIME > #{startTime}
</select>
```

| 항목 | MyBatis | JPQL |
|------|---------|------|
| 대상 | 테이블명 (TB_NEXCLASS_...) | 엔티티 클래스명 (HostAssignment) |
| 컬럼 | DB 컬럼명 (HOST_EMAIL) | 자바 필드명 (hostEmail) |
| 파라미터 | #{파라미터} | :파라미터 + @Param |

### 3.2 네이티브 쿼리 — 진짜 SQL

JPQL로 안 될 때 (DB 함수, 복잡한 서브쿼리):

```java
@Query(value = "SELECT * FROM TB_NEXCLASS_TERM WHERE TERM_YEAR = :year",
       nativeQuery = true)
List<Term> findByYear(@Param("year") String year);
```

`nativeQuery = true` 넣으면 진짜 SQL. 테이블명, 컬럼명 그대로 쓸 수 있어.
근데 이거 쓰면 DB 종류 바꿀 때 수정해야 해. 최후의 수단으로만.

### 3.3 페이징 — Pageable

51,683명 사용자를 한 번에 가져오면? 서버 터져. 페이징 해야 해.

```java
@Repository
public interface UserRepository extends JpaRepository<User, String> {
    Page<User> findByUserType(String userType, Pageable pageable);
}
```

```java
// Service에서 사용
Pageable pageable = PageRequest.of(0, 1000);  // 0페이지부터 1000건씩
Page<User> page = userRepository.findByUserType("STUDENT", pageable);

List<User> users = page.getContent();     // 실제 데이터
int totalPages = page.getTotalPages();     // 전체 페이지 수
long totalCount = page.getTotalElements(); // 전체 건수
```

MyBatis였으면 LIMIT, OFFSET SQL 직접 짜야 해. JPA는 Pageable 넘기면 자동.

### 3.4 정렬 — Sort

```java
// 이름순 정렬
List<User> users = userRepository.findAll(Sort.by("userName"));

// 생성일 역순
List<User> users = userRepository.findAll(Sort.by(Sort.Direction.DESC, "createdAt"));

// 페이징 + 정렬
Pageable pageable = PageRequest.of(0, 1000, Sort.by("userName"));
```

### 3.5 @Modifying — 벌크 UPDATE/DELETE

```java
@Modifying
@Query("UPDATE User u SET u.enrolledYn = 'N' WHERE u.userType = :type")
int bulkUpdateEnrolled(@Param("type") String type);
```

여러 건 한 번에 수정. 변경 감지로 하나씩 UPDATE 하면 느리니까 벌크로.
`@Modifying` 필수 — 이거 없으면 에러.

---

## 4. 주의사항 / 함정

**함정 1: JPQL에서 테이블명/컬럼명 쓰기**
```java
@Query("SELECT * FROM TB_NEXCLASS_TERM")  // ❌ 이건 SQL
@Query("SELECT t FROM Term t")             // ✅ 이게 JPQL
```

**함정 2: @Param 빼먹기**
파라미터가 2개 이상이면 @Param 필수. 안 쓰면 어떤 파라미터인지 JPA가 모름.

**함정 3: @Modifying 없이 UPDATE/DELETE**
@Query로 UPDATE/DELETE 쿼리 쓸 때 @Modifying 안 붙이면 에러.

**함정 4: 벌크 연산 후 영속성 컨텍스트 불일치**
벌크 UPDATE는 영속성 컨텍스트를 건너뛰고 DB 직접 수정. 캐시에 있는 엔티티는 여전히 옛날 값. `@Modifying(clearAutomatically = true)` 써서 캐시 날려.

---

## 5. 정리

| 방법 | 용도 | 예시 |
|------|------|------|
| 쿼리 메서드 | 단순 WHERE | findByHostStatus() |
| @Query JPQL | 복잡한 조건 | @Query("SELECT a FROM...") |
| @Query native | DB 전용 기능 | nativeQuery = true |
| Pageable | 페이징 | PageRequest.of(0, 1000) |
| @Modifying | 벌크 UPDATE/DELETE | 여러 건 한 번에 |

> **쿼리 메서드로 안 되면 @Query JPQL, 그래도 안 되면 네이티브 쿼리. 단계별로 올라가되, 최대한 낮은 단계에서 해결해.**

---

### 확인 문제

**Q1.** JPQL과 SQL의 핵심 차이 하나만.

**Q2.** @Param은 언제 필요해?

**Q3.** 51,683명을 1000건씩 페이징하려면?

**Q4.** @Modifying은 언제 써?

??? success "정답 보기"

    **A1.** SQL은 테이블/컬럼 대상, JPQL은 엔티티 클래스/필드 대상.

    **A2.** @Query에서 파라미터가 2개 이상일 때. :paramName과 메서드 파라미터를 연결.

    **A3.** `PageRequest.of(0, 1000)` → 0페이지부터 1000건씩. 약 52페이지.

    **A4.** @Query로 UPDATE/DELETE 쿼리 실행할 때 필수.
