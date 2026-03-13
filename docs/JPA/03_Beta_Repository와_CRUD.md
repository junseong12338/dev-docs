# 03. Repository와 CRUD - Beta

---

## 1. 이게 뭐야? — "인터페이스 하나면 CRUD 끝"

MyBatis: Mapper 인터페이스 만들고, XML에 SQL 써야 하고, VO도 만들어야 하고... 파일이 3개.
JPA: **Repository 인터페이스 하나 선언하면 CRUD 메서드가 자동으로 생겨.** SQL 안 짜도 돼.

```
MyBatis:  Mapper 인터페이스 + XML 파일 + VO = 3개 파일
JPA:      Repository 인터페이스 1개 = 끝
```

어떻게 가능하냐고? Spring Data JPA가 네가 선언한 인터페이스를 보고 구현체를 **자동 생성**해.

---

## 2. 어떻게 돌아가?

```
네가 만드는 것:
  public interface TermRepository extends JpaRepository<Term, String> { }

Spring Data JPA가 알아서 만드는 것:
  TermRepositoryImpl (구현체) ← 네 눈에 안 보임
    - save(term) → INSERT or UPDATE SQL 생성
    - findById("2026-1") → SELECT ... WHERE TERM_CD = '2026-1'
    - findAll() → SELECT * FROM TB_NEXCLASS_TERM
    - delete(term) → DELETE FROM TB_NEXCLASS_TERM WHERE TERM_CD = ?
    - count() → SELECT COUNT(*) FROM TB_NEXCLASS_TERM
```

### JpaRepository<Term, String> 제네릭 의미

```java
JpaRepository<Term, String>
              ^^^^  ^^^^^^
              │     └── PK 타입 (Term의 @Id 필드 타입)
              └── 엔티티 클래스
```

| Repository | 엔티티 | PK 타입 | 이유 |
|-----------|--------|---------|------|
| JpaRepository<Term, **String**> | Term | String | termCd가 String |
| JpaRepository<SyncLog, **Long**> | SyncLog | Long | syncId가 Long |

---

## 3. 코드로 보자

### 3.1 기본 Repository — NexClass TermRepository.java

```java
@Repository
public interface TermRepository extends JpaRepository<Term, String> {
    // 아무것도 안 써도 CRUD 자동 제공
}
```

이게 진짜 전부야. 이 인터페이스 하나로:

| 메서드 | 하는 일 | 생성되는 SQL |
|--------|---------|------------|
| save(term) | 저장 (INSERT or UPDATE) | INSERT INTO ... / UPDATE ... SET ... |
| findById("2026-1") | PK로 조회 | SELECT ... WHERE TERM_CD = '2026-1' |
| findAll() | 전체 조회 | SELECT * FROM TB_NEXCLASS_TERM |
| delete(term) | 삭제 | DELETE FROM ... WHERE TERM_CD = ? |
| count() | 개수 | SELECT COUNT(*) FROM ... |

### 3.2 save()의 마법 — UPSERT

```java
// 새 데이터 (PK가 DB에 없음) → INSERT
Term newTerm = Term.builder().termCd("2026-NEW").termName("신규학기").build();
termRepository.save(newTerm);  // INSERT INTO TB_NEXCLASS_TERM ...

// 기존 데이터 (PK가 DB에 있음) → UPDATE
Term existing = termRepository.findById("2026-1").orElseThrow();
existing.setTermName("수정된 학기명");
termRepository.save(existing);  // UPDATE TB_NEXCLASS_TERM SET ... WHERE TERM_CD = '2026-1'
```

MyBatis였으면:
```java
termMapper.insertTerm(newTerm);     // INSERT 따로
termMapper.updateTerm(existing);    // UPDATE 따로 + SQL도 따로 작성
```

JPA는 save() 하나. PK 존재 여부로 INSERT/UPDATE 자동 판단.

### 3.3 findById()와 Optional

```java
// findById는 Optional을 반환해
Optional<Term> optionalTerm = termRepository.findById("2026-1");

// 없으면 예외 던지기 — 가장 많이 쓰는 패턴
Term term = termRepository.findById("2026-1")
    .orElseThrow(() -> new RuntimeException("학기를 찾을 수 없습니다"));
```

MyBatis는 없으면 null 반환. JPA는 Optional로 감싸서 **null 실수를 방지**해.

### 3.4 쿼리 메서드 — 메서드 이름으로 쿼리 자동 생성

```java
@Repository
public interface HostPoolRepository extends JpaRepository<HostPool, String> {
    // 메서드 이름만 쓰면 JPA가 SQL 자동 생성!
    List<HostPool> findByHostStatus(String hostStatus);
    // → SELECT * FROM TB_NEXCLASS_HOST_POOL WHERE HOST_STATUS = ?
}
```

```java
@Repository
public interface CourseUserRepository extends JpaRepository<CourseUser, Long> {
    List<CourseUser> findByCourseCd(String courseCd);
    // → SELECT * FROM TB_NEXCLASS_COURSE_USER WHERE COURSE_CD = ?
}
```

### 네이밍 규칙

| 메서드 이름 | 생성되는 WHERE |
|------------|---------------|
| findByHostStatus(status) | WHERE HOST_STATUS = ? |
| findByCourseCd(cd) | WHERE COURSE_CD = ? |
| findByUserType(type) | WHERE USER_TYPE = ? |
| findByCourseCdAndUserCd(cd, ucd) | WHERE COURSE_CD = ? AND USER_CD = ? |
| findByTermNameContaining(name) | WHERE TERM_NAME LIKE '%name%' |
| findByCreatedAtAfter(date) | WHERE CREATED_AT > ? |
| countByUserType(type) | SELECT COUNT(*) WHERE USER_TYPE = ? |

규칙: **findBy + 필드명(카멜케이스)** → JPA가 WHERE 조건 자동 생성.

MyBatis였으면 이것들 전부 XML에 SQL 하나하나 작성해야 해.

### 3.5 @Query — 복잡한 쿼리

메서드 이름으로 안 되는 복잡한 쿼리? @Query 써.

```java
@Repository
public interface HostAssignmentRepository extends JpaRepository<HostAssignment, Long> {

    // JPQL — 엔티티 기준 쿼리 (테이블명 아니고 클래스명!)
    @Query("SELECT a.hostEmail FROM HostAssignment a WHERE a.startTime < :endTime AND a.endTime > :startTime")
    List<String> findAssignedHostEmails(
        @Param("startTime") LocalDateTime startTime,
        @Param("endTime") LocalDateTime endTime
    );
}
```

MyBatis XML과 비교:
```xml
<!-- MyBatis는 테이블명 + 컬럼명 -->
<select id="findAssignedHostEmails">
    SELECT HOST_EMAIL FROM TB_NEXCLASS_HOST_ASSIGNMENT
    WHERE START_TIME < #{endTime} AND END_TIME > #{startTime}
</select>
```

차이: JPQL은 **테이블명이 아니라 엔티티 클래스명**을 쓴다. `HostAssignment`(클래스), `a.hostEmail`(필드).

---

## 4. 주의사항 / 함정

**함정 1: 메서드 이름 오타**
findByHostStatus → ✅ (hostStatus 필드 존재)
findByHostState → ❌ (없는 필드 → 앱 시작 시 에러)
JPA가 메서드 이름으로 쿼리 만드니까, 필드명 틀리면 바로 에러.

**함정 2: @Query에서 테이블명 쓰기**
```java
@Query("SELECT * FROM TB_NEXCLASS_TERM")  // ❌ 이건 SQL이야
@Query("SELECT t FROM Term t")             // ✅ 이게 JPQL (엔티티명)
```

**함정 3: Optional 무시**
```java
Term term = termRepository.findById("없는코드").get();  // ❌ NoSuchElementException
Term term = termRepository.findById("없는코드").orElseThrow();  // ✅ 명시적 예외
```

---

## 5. 정리

| MyBatis | JPA |
|---------|-----|
| Mapper 인터페이스 + XML | Repository 인터페이스만 |
| SQL 직접 작성 | save/findById/findAll/delete 자동 |
| 조건 검색 → XML에 SELECT 추가 | findBy필드명() 메서드명으로 자동 |
| 복잡한 쿼리 → XML에 작성 | @Query로 JPQL 작성 |
| null 반환 | Optional 반환 |

> **JpaRepository 인터페이스 하나 상속하면 CRUD가 자동이고, 메서드 이름으로 WHERE 조건까지 자동 생성된다.**

---

### 확인 문제

**Q1.** JpaRepository<Term, String>에서 String은 뭘 의미해?

**Q2.** save()가 INSERT/UPDATE를 어떻게 구분해?

**Q3.** findByHostStatus("ACTIVE")는 어떤 SQL이 생성돼?

**Q4.** @Query에서 테이블명 대신 뭘 써야 해?

??? success "정답 보기"

    **A1.** Term 엔티티의 PK(@Id) 필드 타입. termCd가 String이니까 String.

    **A2.** PK 값이 DB에 있으면 UPDATE, 없으면 INSERT. (정확히는 PK가 null이거나 DB에 없으면 INSERT)

    **A3.** SELECT * FROM TB_NEXCLASS_HOST_POOL WHERE HOST_STATUS = 'ACTIVE'

    **A4.** 엔티티 클래스명. TB_NEXCLASS_TERM이 아니라 Term. 컬럼명 대신 필드명.
