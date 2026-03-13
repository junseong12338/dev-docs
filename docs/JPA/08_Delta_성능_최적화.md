# 08. 성능 최적화 - Delta

---

## 1. 이게 뭐야? — "DB 왕복 줄이기"

JPA는 편하지만 성능 함정이 있어. 특히 **N+1 문제**. 이거 모르면 운영 서버에서 DB 터져.

핵심: **DB에 몇 번 왕복하느냐**가 성능을 결정해. 1번 갈 걸 101번 가면 100배 느려.

---

## 2. N+1 문제 — JPA 최대 함정

### 상황

학기 10개를 조회하고, 각 학기의 과목 목록을 가져온다고 치자.

```java
List<Term> terms = termRepository.findAll();      // 1번 SQL
for (Term term : terms) {
    List<Course> courses = term.getCourses();      // 10번 SQL (학기마다 1번)
}
// 총 11번 SQL 실행! (1 + N = 1 + 10)
```

학기 100개면? **101번 SQL**. 이게 N+1 문제.

MyBatis는 이 문제가 없어. SQL을 네가 직접 짜니까 JOIN으로 1번에 끝내거든. JPA는 편한 만큼 이 함정이 있어.

### 해결: fetch join

```java
@Query("SELECT t FROM Term t JOIN FETCH t.courses")
List<Term> findAllWithCourses();
// → 1번 SQL로 학기 + 과목 한 방에!
```

```sql
-- JPA가 생성하는 SQL
SELECT t.*, c.*
FROM TB_NEXCLASS_TERM t
JOIN TB_NEXCLASS_COURSE c ON t.TERM_CD = c.TERM_CD
```

N+1번 → **1번**으로 줄어듬.

---

## 3. 지연 로딩 vs 즉시 로딩

### LAZY (지연 로딩) — 기본값, 권장

```java
@ManyToOne(fetch = FetchType.LAZY)    // 실제로 접근할 때 SQL
private Term term;
```

course.getTerm() 호출하는 순간에 SQL 실행. 안 쓰면 SQL 안 나감.

### EAGER (즉시 로딩) — 위험

```java
@ManyToOne(fetch = FetchType.EAGER)   // 조회 시 무조건 함께
private Term term;
```

Course 조회하면 Term도 무조건 같이 가져옴. 안 필요해도.
이게 N+1의 주범이야. **EAGER 쓰지 마.**

| 방식 | SQL 시점 | 장점 | 단점 |
|------|----------|------|------|
| **LAZY** | 접근할 때 | 불필요한 쿼리 안 나감 | 트랜잭션 밖에서 접근 시 에러 |
| EAGER | 즉시 | 항상 데이터 있음 | N+1 문제, 불필요한 JOIN |

---

## 4. 배치 처리 — 대량 데이터

NexClass 동기화: 사용자 51,683명. 하나씩 save() 하면?

```java
// ❌ 느림 — 51,683번 INSERT
for (User user : userList) {
    userRepository.save(user);
}

// ✅ 빠름 — 배치 INSERT
userRepository.saveAll(userList);
```

`saveAll()`은 내부적으로 배치 처리. 하지만 **IDENTITY 전략(AUTO_INCREMENT)은 배치 INSERT 불가**. JPA가 INSERT 후 생성된 ID를 바로 알아야 해서 한 건씩 실행됨.

String PK(Term, Course, User)는 배치 가능. Long PK + IDENTITY(CourseUser, SyncLog)는 배치 제한.

### application.yml 배치 설정

```yaml
spring:
  jpa:
    properties:
      hibernate:
        jdbc:
          batch_size: 1000        # 1000건씩 묶어서 INSERT
        order_inserts: true       # INSERT 순서 최적화
        order_updates: true       # UPDATE 순서 최적화
```

---

## 5. 벌크 연산

변경 감지로 하나씩 UPDATE → 느림. 한 방에 업데이트:

```java
@Modifying(clearAutomatically = true)
@Query("UPDATE User u SET u.enrolledYn = 'N' WHERE u.userType = :type")
int bulkUpdateEnrolled(@Param("type") String type);
// → 1번 SQL로 수천 건 UPDATE
```

`clearAutomatically = true` — 벌크 연산 후 영속성 컨텍스트 비우기. 안 하면 캐시에 옛날 값 남아있어서 버그.

---

## 6. 주의사항 / 함정

**함정 1: EAGER 기본 설정**
@ManyToOne의 기본 fetch는 **EAGER**야. 명시적으로 LAZY 지정 안 하면 N+1 먹어.
```java
@ManyToOne                              // ❌ 기본이 EAGER
@ManyToOne(fetch = FetchType.LAZY)      // ✅ 명시적 LAZY
```

**함정 2: fetch join + 페이징**
fetch join에 페이징(Pageable) 쓰면 JPA가 메모리에서 페이징함. 데이터 많으면 메모리 터져.

**함정 3: IDENTITY 전략 배치 불가**
AUTO_INCREMENT PK는 배치 INSERT 안 됨. 성능 중요하면 TABLE 전략이나 String PK 고려.

---

## 7. 정리

| 문제 | 해결 |
|------|------|
| N+1 | fetch join, @EntityGraph |
| EAGER 함정 | LAZY로 변경 |
| 대량 INSERT 느림 | saveAll() + batch_size 설정 |
| 대량 UPDATE 느림 | @Modifying 벌크 연산 |

### JPA vs MyBatis 성능 트레이드오프

| 항목 | MyBatis | JPA |
|------|---------|-----|
| N+1 문제 | 없음 (SQL 직접 작성) | 있음 (fetch join으로 해결) |
| 배치 처리 | SQL로 자유 | IDENTITY 전략 제한 |
| 성능 튜닝 | SQL 직접 최적화 | JPQL/설정으로 간접 최적화 |
| 복잡한 쿼리 | 강함 | 약함 (네이티브 쿼리 필요) |

> **JPA 성능의 80%는 N+1 해결이다. LAZY + fetch join만 알면 대부분 해결된다.**

---

### 확인 문제

**Q1.** N+1 문제가 뭐야? 학기 10개, 각 학기에 과목이 있을 때 SQL 몇 번?

**Q2.** fetch join이 N+1을 어떻게 해결해?

**Q3.** @ManyToOne의 기본 fetch 전략은? 왜 위험?

**Q4.** IDENTITY 전략에서 배치 INSERT가 안 되는 이유?

??? success "정답 보기"

    **A1.** 목록 조회 1번 + 각 항목마다 연관 조회 N번 = N+1번. 학기 10개면 11번 SQL.

    **A2.** JOIN으로 한 방에 가져오니까 SQL 1번으로 끝. N+1번 → 1번.

    **A3.** EAGER. 연관 엔티티를 무조건 함께 가져와서 N+1의 주범. 명시적으로 LAZY 설정해야.

    **A4.** AUTO_INCREMENT는 INSERT 해봐야 PK를 알 수 있어. JPA는 영속성 관리를 위해 PK를 바로 알아야 해서 한 건씩 INSERT 후 PK를 읽어옴.
