# 02. 엔티티 기초 - Alpha

---

## 1. 이게 뭐야? — "DB 테이블의 자바 분신"

MyBatis VO는 그냥 데이터 담는 그릇이야. "내가 어떤 테이블인지" 몰라. XML resultMap이 알려줘야 해.

JPA 엔티티는 **자기가 어떤 테이블인지 스스로 아는 그릇**. 어노테이션으로 다 적혀있어.

```
MyBatis:  TermVO.java (그냥 그릇) ← XML resultMap → DB 테이블
JPA:      Term.java (@Entity — 자기가 테이블 정보를 앎) ↔ DB 테이블
```

---

## 2. 어떻게 돌아가? — 어노테이션 역할

```
@Entity                           → "나는 DB 테이블과 매핑되는 클래스야"
@Table(name = "TB_NEXCLASS_TERM") → "테이블명은 이거야"
@Id                               → "이 필드가 PK야"
@GeneratedValue(IDENTITY)         → "PK는 DB AUTO_INCREMENT가 만들어"
@Column(name = "TERM_CD")        → "이 필드는 이 컬럼이야"
@PrePersist                       → "INSERT 직전에 이 메서드 자동 실행"
@PreUpdate                        → "UPDATE 직전에 이 메서드 자동 실행"
```

### MyBatis vs JPA 매핑 비교

| 하는 일 | MyBatis | JPA |
|---------|---------|-----|
| "이거 테이블이야" | XML `<resultMap type="TermVO">` | `@Entity` + `@Table` |
| "이 필드 = 이 컬럼" | `<result property="termCd" column="TERM_CD"/>` | `@Column(name = "TERM_CD")` |
| "이게 PK야" | `<id property="termCd" column="TERM_CD"/>` | `@Id` |
| "PK 자동 생성" | `useGeneratedKeys="true"` | `@GeneratedValue(IDENTITY)` |
| "저장 전 시간 세팅" | Service에서 `vo.setCreatedAt(new Date())` 직접 | `@PrePersist`가 알아서 |

---

## 3. 코드로 보자

### 3.1 @Entity + @Table

```java
@Entity                                    // JPA야, 이 클래스 관리해
@Table(name = "TB_NEXCLASS_TERM")          // 실제 DB 테이블명
public class Term { ... }
```

@Entity 없으면 JPA가 무시해. 그냥 일반 클래스 취급.

### 3.2 @Id — PK 지정

**String PK — 외부 시스템이 PK 결정 (NexClass Term.java):**
```java
@Id                                        // 이 필드가 PK
@Column(name = "TERM_CD", length = 40)
private String termCd;                     // LMS에서 코드값 넘어옴 → 네가 직접 세팅
```

**Long PK — DB가 자동 생성 (NexClass SyncLog.java):**
```java
@Id
@GeneratedValue(strategy = GenerationType.IDENTITY)  // AUTO_INCREMENT
@Column(name = "SYNC_ID")
private Long syncId;                       // 값 안 넣어도 DB가 1, 2, 3... 채움
```

### 3.3 @GeneratedValue 전략

| 전략 | 의미 | DB | MyBatis 비교 |
|------|------|-----|-------------|
| **IDENTITY** | AUTO_INCREMENT | MySQL/MariaDB | useGeneratedKeys="true" |
| SEQUENCE | DB 시퀀스 | Oracle/PostgreSQL | nextval 직접 호출 |
| TABLE | 채번 테이블 | 범용 (거의 안 씀) | - |
| AUTO | DB에 맞게 알아서 | 범용 | - |

NexClass = MariaDB → **IDENTITY**.

### 3.4 @Column 옵션

```java
@Column(name = "TERM_CD", length = 40)           // 문자열: name + length
@Column(name = "RECORD_COUNT")                     // 숫자: name만 (length 불필요)
@Column(name = "SYNCED_AT")                        // 날짜: name만
@Column(name = "CREATED_AT", updatable = false)    // 수정 시 이 컬럼 안 건드림
@Column(name = "ERROR_MESSAGE", columnDefinition = "TEXT")  // DB 타입 직접 지정
```

**DDL이 진실이야. @Column의 length는 DDL VARCHAR 길이와 맞춰.**

### 3.5 필드 타입 매핑

| Java | DB | 예시 |
|------|-----|------|
| String | VARCHAR | termCd, termName |
| Long | BIGINT | syncId, id |
| Integer | INT | recordCount |
| LocalDateTime | DATETIME | createdAt, syncedAt |

### 3.6 @PrePersist / @PreUpdate

```java
@PrePersist
protected void onCreate() {
    createdAt = LocalDateTime.now();     // 생성 시간 자동
    updatedAt = LocalDateTime.now();
    if (useYn == null) useYn = "Y";     // 기본값 자동
}

@PreUpdate
protected void onUpdate() {
    updatedAt = LocalDateTime.now();     // 수정 시간만 갱신
}
```

MyBatis였으면 Service에서 매번 직접:
```java
vo.setCreatedAt(new Date());
vo.setUpdatedAt(new Date());
termMapper.insertTerm(vo);
```

JPA는 엔티티가 알아서 해. Service가 신경 안 써도 돼.

### 3.7 Lombok

```java
@Getter              // getter 자동 생성
@Setter              // setter 자동 생성
@Builder             // .builder().termCd("2026").build() 패턴
@NoArgsConstructor   // 기본 생성자 (JPA 필수!)
@AllArgsConstructor  // 모든 필드 생성자 (@Builder가 필요)
```

---

## 4. 주의사항 / 함정

**함정 1: @NoArgsConstructor 빠뜨림**
JPA가 엔티티 못 만들어서 앱 시작 시 에러.

**함정 2: @Column length와 DB 불일치**
length = 50인데 DB가 VARCHAR(40)이면? 에러 안 남. 근데 50글자 넣으면 DB에서 잘림. DDL 기준으로 맞출 것.

**함정 3: @Id 없는 엔티티**
@Entity 있는데 @Id 없으면 앱 시작 시 에러.

**함정 4: Long vs long**
```java
private Long syncId;   // ✅ null 가능 (새 엔티티는 PK null)
private long syncId;   // ❌ 기본값 0 → JPA가 새 건지 기존 건지 구분 못 함
```
PK는 반드시 **래퍼 타입(Long)**.

---

## 5. 정리

### PK 전략 가이드

| 상황 | 타입 | 어노테이션 | NexClass |
|------|------|-----------|----------|
| 외부 시스템이 PK 결정 | String | @Id만 | Term, Course, User |
| DB 자동 생성 | Long | @Id + @GeneratedValue | CourseUser, SyncLog |

> **JPA 엔티티는 DB 테이블의 자바 분신이다. 어노테이션으로 자기가 어떤 테이블이고, 어떤 컬럼인지 스스로 안다.**

---

### 확인 문제

**Q1.** Term.java는 @Id만, SyncLog.java는 @Id + @GeneratedValue. 왜?

**Q2.** @Column(updatable = false)는 뭘 의미?

**Q3.** @PrePersist를 MyBatis 방식으로 표현하면?

**Q4.** PK를 `long` (원시 타입)으로 쓰면 왜 문제?

??? success "정답 보기"

    **A1.** Term은 LMS에서 코드값이 넘어와서 외부가 PK 결정 → @Id만. SyncLog는 내부 관리용이라 DB AUTO_INCREMENT → @GeneratedValue.

    **A2.** UPDATE 시 이 컬럼을 SET 절에 안 넣겠다. CREATED_AT처럼 수정하면 안 되는 필드에 사용.

    **A3.** Service에서 INSERT 전에 직접 `vo.setCreatedAt(new Date())` 코드 작성. JPA는 이걸 엔티티가 알아서.

    **A4.** long은 null 불가(기본값 0). JPA는 PK가 null이면 INSERT, 값 있으면 UPDATE로 판단하는데, 항상 0이 들어가면 구분 못 함.
