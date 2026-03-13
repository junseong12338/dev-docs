# 04. 연관관계 기초 - Beta

---

## 1. 이게 뭐야? — "객체로 FK 표현하기"

DB에서 FK(외래키) 알지? TB_NEXCLASS_COURSE에 TERM_CD가 있어서 TB_NEXCLASS_TERM을 참조하는 거.

MyBatis: JOIN SQL 직접 짜고, resultMap에서 수동으로 매핑.
JPA: 어노테이션 하나면 자바 객체가 직접 다른 객체를 참조할 수 있어.

```
DB:    COURSE 테이블 --- TERM_CD(FK) --→ TERM 테이블
JPA:   Course 객체  --- term 필드   --→ Term 객체
```

---

## 2. 어떻게 돌아가?

### 관계 종류

```
@ManyToOne  — 다대일 (가장 많이 씀)
  "여러 과목이 하나의 학기에 속한다"
  Course(다) → Term(일)

@OneToMany  — 일대다 (반대 방향)
  "하나의 학기에 여러 과목이 있다"
  Term(일) → List<Course>(다)

@OneToOne   — 일대일 (드물게 사용)
@ManyToMany — 다대다 (실무에서 거의 안 씀, 중간 테이블로 풀어)
```

### 단방향 vs 양방향

```
단방향: Course → Term (한쪽에서만 참조)
양방향: Course ↔ Term (양쪽에서 서로 참조, mappedBy 필요)
```

실무에서는 **단방향 @ManyToOne만으로 90% 해결**됨.

---

## 3. 코드로 보자

### 3.1 연관관계 없는 현재 NexClass 방식

```java
// 현재 Course.java — FK를 그냥 String으로 저장
@Column(name = "TERM_CD", length = 40)
private String termCd;   // 학기 코드 값만 갖고 있음
```

학기 정보 필요하면? 별도로 조회해야 해:
```java
Course course = courseRepository.findById("CRS001").orElseThrow();
Term term = termRepository.findById(course.getTermCd()).orElseThrow();  // 따로 조회
```

### 3.2 @ManyToOne 연관관계 설정하면

```java
// Course.java — 연관관계 버전
@ManyToOne                            // "여러 과목이 하나의 학기"
@JoinColumn(name = "TERM_CD")        // FK 컬럼명
private Term term;                    // String이 아니라 Term 객체!
```

학기 정보? 바로 접근:
```java
Course course = courseRepository.findById("CRS001").orElseThrow();
String termName = course.getTerm().getTermName();  // 바로 접근!
```

### 3.3 @OneToMany (반대 방향)

```java
// Term.java — 양방향 설정 시
@OneToMany(mappedBy = "term")         // Course.term 필드가 주인이야
private List<Course> courses;          // 이 학기의 과목 목록
```

```java
Term term = termRepository.findById("2026-1").orElseThrow();
List<Course> courses = term.getCourses();  // 이 학기의 모든 과목
```

### MyBatis 비교

```xml
<!-- MyBatis: JOIN SQL 직접 작성 -->
<select id="selectCourseWithTerm" resultMap="courseTermMap">
    SELECT c.COURSE_CD, c.COURSE_NAME, t.TERM_NAME
    FROM TB_NEXCLASS_COURSE c
    JOIN TB_NEXCLASS_TERM t ON c.TERM_CD = t.TERM_CD
    WHERE c.COURSE_CD = #{courseCd}
</select>
```

JPA: 어노테이션만 붙이면 `course.getTerm()` 한 줄로 끝.

---

## 4. 주의사항 / 함정

**함정 1: 양방향 무한루프**
Course → Term → courses → Course → Term → ... toString()이나 JSON 변환 시 무한루프. @ToString.Exclude, @JsonIgnore로 끊어야 함.

**함정 2: N+1 문제**
Course 100개 조회 → 각 course.getTerm() 할 때마다 SQL 1개씩 = 101개 SQL. 이건 Ch08에서 깊게 다룸.

**함정 3: 연관관계 주인 헷갈림**
FK가 있는 쪽이 주인. COURSE 테이블에 TERM_CD(FK)가 있으니까 Course가 주인. @OneToMany 쪽에 mappedBy 붙이는 거야.

---

## 5. 정리

### 왜 NexClass에서는 연관관계 안 썼나?

| 기준 | 판단 |
|------|------|
| 데이터 용도 | LMS에서 동기화해서 저장만 (복잡한 JOIN 불필요) |
| 조회 패턴 | 과목 목록, 사용자 목록 — 단순 조회 위주 |
| 복잡도 | 연관관계 쓰면 N+1, 지연 로딩 등 관리 포인트 증가 |
| YAGNI | 지금 안 필요한 기능 미리 만들지 않는다 |

→ String FK로 충분. 연관관계는 **복잡한 객체 그래프 탐색이 필요할 때** 쓰는 거야.

> **연관관계는 자바 객체로 FK를 표현하는 것. 편하지만 N+1 함정이 있어서, 안 필요하면 안 쓰는 게 낫다.**

---

### 확인 문제

**Q1.** @ManyToOne은 어떤 관계? Course → Term 기준으로 설명.

**Q2.** 연관관계의 "주인"은 누구고 왜?

**Q3.** NexClass에서 연관관계 대신 String termCd를 쓴 이유?

??? success "정답 보기"

    **A1.** 다대일. 여러 Course가 하나의 Term에 속하는 관계. Course 쪽에 @ManyToOne 붙임.

    **A2.** FK가 있는 쪽이 주인. COURSE 테이블에 TERM_CD(FK) 있으니까 Course가 주인. Term 쪽 @OneToMany에 mappedBy 붙임.

    **A3.** LMS 동기화 데이터라 단순 저장이 목적. 복잡한 객체 그래프 탐색 불필요. 연관관계 쓰면 N+1 등 관리 포인트만 늘어남 (YAGNI).
