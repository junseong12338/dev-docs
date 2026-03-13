# 02. SQL 기초: DDL / DML / DCL

---

## 1. SQL이란?

### 1.1 정의

!!! note "SQL 정의"
    **SQL** = Structured Query Language = 구조화된 질의 언어 = DB에게 명령을 내리는 언어

프로그래밍 언어(Java, Python)와 다른 점:

!!! example "Java vs SQL 비교"
    **Java**: "이렇게 해라" (How - 절차적)
    → for문 돌면서 하나씩 비교해서 찾아라

    **SQL**: "이걸 줘" (What - 선언적)
    → 조건에 맞는 데이터 줘. 어떻게 찾는지는 DB가 알아서.

### 1.2 SQL의 역사

!!! note "SQL의 역사"
    - 1970: E.F. Codd가 관계형 모델 논문 발표
    - 1974: IBM에서 SEQUEL 개발 (SQL의 원래 이름)
    - 1979: Oracle이 최초 상용 RDBMS 출시
    - 1986: SQL이 ANSI 표준으로 채택 (SQL-86)
    - 이후: SQL-92, SQL:1999, SQL:2003, SQL:2016 ...

    → SQL은 50년 된 언어다. 그리고 아직도 쓴다.
    → 프레임워크가 바뀌고 언어가 바뀌어도 SQL은 그대로다.
    → SQL 잘하면 밥 굶을 일 없다.

---

## 2. SQL 명령어 분류

SQL은 역할에 따라 크게 3가지 (+1)로 나뉜다.

!!! note "SQL 명령어 분류"
    **DDL (Data Definition Language)** - 구조 정의

    - `CREATE` - 만든다
    - `ALTER` - 바꾼다
    - `DROP` - 부순다
    - `TRUNCATE` - 비운다
    - `RENAME` - 이름 바꾼다

    **DML (Data Manipulation Language)** - 데이터 조작

    - `SELECT` - 조회한다
    - `INSERT` - 넣는다
    - `UPDATE` - 고친다
    - `DELETE` - 지운다

    **DCL (Data Control Language)** - 권한 제어

    - `GRANT` - 권한 준다
    - `REVOKE` - 권한 뺏는다

    **TCL (Transaction Control Language)** - 트랜잭션 제어

    - `COMMIT` - 확정한다
    - `ROLLBACK` - 되돌린다
    - `SAVEPOINT` - 중간 저장점

### 2.1 비유

!!! example "비유로 이해하기"
    **DDL** = 건물(테이블) 자체를 짓고/개조하고/철거하는 것
    → 건축 허가 필요, 한번 하면 되돌리기 어려움

    **DML** = 건물 안의 가구(데이터)를 넣고/옮기고/빼는 것
    → 가구 배치 중 마음에 안 들면 원래대로 되돌릴 수 있음

    **DCL** = 건물의 출입증을 발급하고/회수하는 것
    → 누가 어디에 들어갈 수 있는지

    **TCL** = "이 배치 확정" 또는 "원래대로 되돌려" 명령
    → 가구 배치(DML)에 대해서만 동작

---

## 3. DDL 상세 (Data Definition Language)

### 3.1 핵심 특성

!!! warning "DDL의 핵심 특성"
    1. **Auto-Commit** -- 실행하는 순간 자동으로 COMMIT됨. ROLLBACK 불가. "앗 실수!" 해도 되돌릴 수 없음
    2. **구조를 변경** -- 데이터가 아니라 테이블/인덱스/뷰 등의 구조. 메타데이터를 변경하는 것
    3. **Metadata Lock 필요** -- 구조 변경이니까 다른 세션의 접근을 차단해야 함. 이게 우리가 겪은 문제의 원인

### 3.2 CREATE — 만든다

```sql
-- 테이블 생성
CREATE TABLE tb_student (
    std_no    VARCHAR(20)  NOT NULL,
    std_nm    VARCHAR(50)  NOT NULL,
    dept_cd   VARCHAR(10),
    reg_dttm  DATETIME     DEFAULT NOW(),
    PRIMARY KEY (std_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 인덱스 생성
CREATE INDEX idx_student_dept ON tb_student(dept_cd);

-- DB(스키마) 생성
CREATE DATABASE lxpknu10 DEFAULT CHARACTER SET utf8mb4;

-- 뷰 생성
CREATE VIEW v_student_info AS
SELECT s.std_no, s.std_nm, d.dept_nm
FROM tb_student s
JOIN tb_department d ON s.dept_cd = d.dept_cd;
```

**CREATE TABLE ... LIKE:**
```sql
-- 기존 테이블과 동일한 구조의 빈 테이블 생성 (데이터 없이)
CREATE TABLE tb_backup LIKE tb_original;
-- 우리가 RENAME 후 빈 테이블 만들 때 이걸 썼다
```

### 3.3 ALTER — 바꾼다

```sql
-- 컬럼 추가
ALTER TABLE tb_student ADD COLUMN email VARCHAR(100) AFTER std_nm;

-- 컬럼 타입 변경
ALTER TABLE tb_student MODIFY COLUMN email VARCHAR(200);

-- 컬럼 이름 + 타입 변경
ALTER TABLE tb_student CHANGE COLUMN email mail_addr VARCHAR(200);

-- 컬럼 삭제
ALTER TABLE tb_student DROP COLUMN email;

-- 인덱스 추가
ALTER TABLE tb_student ADD INDEX idx_dept(dept_cd);

-- 인덱스 삭제
ALTER TABLE tb_student DROP INDEX idx_dept;

-- PK 추가
ALTER TABLE tb_student ADD PRIMARY KEY (std_no);

-- FK 추가
ALTER TABLE tb_student ADD FOREIGN KEY (dept_cd) REFERENCES tb_department(dept_cd);
```

!!! danger "ALTER의 위험성"
    대용량 테이블에 ALTER 하면?

    - 내부적으로 테이블 복사가 발생할 수 있음
    - 2.7억 건 테이블에 ALTER → 수 시간 소요 + 테이블 락
    - 서비스 중에 하면 장애

    MariaDB 10.0+: INSTANT ADD COLUMN 지원 (일부 작업은 빠름)
    하지만 대부분의 ALTER는 여전히 테이블 재구성 필요
    → 서비스 중 ALTER는 반드시 영향도 확인 후 실행

### 3.4 DROP — 부순다

```sql
-- 테이블 삭제 (구조 + 데이터 전부)
DROP TABLE tb_student;

-- 존재할 때만 삭제 (없으면 에러 안 남)
DROP TABLE IF EXISTS tb_student;

-- DB 삭제
DROP DATABASE test_db;

-- 인덱스 삭제
DROP INDEX idx_dept ON tb_student;

-- 뷰 삭제
DROP VIEW v_student_info;
```

!!! danger "DROP의 위험성"
    DROP TABLE은 되돌릴 수 없다.
    테이블 구조 + 데이터 + 인덱스 전부 사라진다.
    백업 없으면 끝이다.

    **프로덕션에서 DROP 칠 때:**

    1. 백업 확인 (반드시)
    2. 의존성 확인 (FK, 뷰, 프로시저에서 참조하는지)
    3. 3번 확인 후 실행

### 3.5 TRUNCATE — 비운다

```sql
-- 테이블 데이터 전부 삭제 (구조는 유지)
TRUNCATE TABLE tb_student;
```

TRUNCATE는 Part 03에서 상세히 다룬다. 여기서는 "DDL이다"만 기억.

### 3.6 RENAME — 이름 바꾼다

```sql
-- 테이블 이름 변경
RENAME TABLE tb_backup TO tb_backup_2026_02_27;

-- 여러 테이블 한 번에 (원자적 — 다 되거나 다 안 되거나)
RENAME TABLE
    tb_backup TO tb_backup_old,
    tb_backup_new TO tb_backup;
```

**실전 활용 (우리가 했던 것):**
```sql
-- 1. 43GB 테이블에 태그 붙이기
RENAME TABLE tb_lms_exam_stare_paper_backup
          TO tb_lms_exam_stare_paper_backup_2026_02_27;

-- 2. 같은 구조의 빈 테이블 만들기
CREATE TABLE tb_lms_exam_stare_paper_backup
LIKE tb_lms_exam_stare_paper_backup_2026_02_27;

-- 서비스는 빈 테이블을 사용 → 정상 동작
-- 구 테이블은 나중에 TRUNCATE 또는 DROP
```

---

## 4. DML 상세 (Data Manipulation Language)

### 4.1 핵심 특성

!!! tip "DML의 핵심 특성"
    1. **트랜잭션 내에서 동작** -- COMMIT 전까지 ROLLBACK 가능. "앗 실수!" 해도 되돌릴 수 있음 (COMMIT 전에만)
    2. **데이터를 조작** -- 테이블 구조는 안 건드림. 행(Row) 단위로 작업
    3. **Undo/Redo 로그 생성** -- 모든 변경을 로그에 기록. ROLLBACK 시 Undo 로그로 복원. 장애 시 Redo 로그로 재실행
    4. **행 레벨 락** -- 수정하는 행만 잠금. 다른 행은 자유롭게 접근 가능

### 4.2 SELECT — 조회한다

```sql
-- 기본 조회
SELECT std_no, std_nm FROM tb_student;

-- 조건 조회
SELECT * FROM tb_student WHERE dept_cd = 'DEPT01';

-- 정렬
SELECT * FROM tb_student ORDER BY std_nm ASC;

-- 그룹핑
SELECT dept_cd, COUNT(*) AS cnt
FROM tb_student
GROUP BY dept_cd
HAVING cnt > 10;

-- 조인
SELECT s.std_nm, d.dept_nm
FROM tb_student s
JOIN tb_department d ON s.dept_cd = d.dept_cd;

-- 서브쿼리
SELECT * FROM tb_student
WHERE dept_cd IN (
    SELECT dept_cd FROM tb_department WHERE dept_nm LIKE '%공학%'
);

-- 페이징
SELECT * FROM tb_student ORDER BY std_no LIMIT 10 OFFSET 20;
```

!!! warning "SELECT 실행 순서 (SQL 작성 순서와 다르다!)"
    | 순서 | 작성 순서 | 실행 순서 |
    |------|-----------|-----------|
    | 1 | SELECT | FROM |
    | 2 | FROM | WHERE |
    | 3 | WHERE | GROUP BY |
    | 4 | GROUP BY | HAVING |
    | 5 | HAVING | SELECT |
    | 6 | ORDER BY | ORDER BY |
    | 7 | LIMIT | LIMIT |

    **왜 중요하냐:**
    SELECT에서 만든 별칭(alias)을 WHERE에서 못 쓰는 이유가 이거다.
    WHERE가 SELECT보다 먼저 실행되니까.

    ```sql
    -- 에러: WHERE에서 cnt 별칭 사용 불가
    SELECT dept_cd, COUNT(*) AS cnt FROM tb_student
    WHERE cnt > 10;  -- 에러!

    -- 정상: HAVING은 SELECT 이후이므로 가능
    SELECT dept_cd, COUNT(*) AS cnt FROM tb_student
    GROUP BY dept_cd
    HAVING cnt > 10;  -- OK!
    ```

### 4.3 INSERT — 넣는다

```sql
-- 기본 삽입
INSERT INTO tb_student (std_no, std_nm, dept_cd)
VALUES ('STD001', '홍길동', 'DEPT01');

-- 여러 행 한 번에
INSERT INTO tb_student (std_no, std_nm, dept_cd) VALUES
('STD002', '김철수', 'DEPT02'),
('STD003', '이영희', 'DEPT01'),
('STD004', '박민수', 'DEPT03');

-- SELECT 결과를 INSERT (우리 백업 SQL이 이거)
INSERT INTO tb_backup
SELECT '백업코드', EXAM_CD, EXAM_QSTN_SN, STD_NO, SCORE
FROM tb_stare_paper
WHERE EXAM_CD = 'EXAM001';

-- ON DUPLICATE KEY UPDATE (있으면 업데이트, 없으면 삽입)
INSERT INTO tb_student (std_no, std_nm) VALUES ('STD001', '홍길동수정')
ON DUPLICATE KEY UPDATE std_nm = '홍길동수정';
```

**INSERT ... SELECT의 위험성 (우리 사례):**
```sql
-- 이 SQL이 1회 실행되면:
INSERT INTO tb_backup SELECT ... FROM tb_paper WHERE exam_cd = #{examCd}
→ 완료 학생 100명 × 문항 50개 = 5,000건 INSERT

-- 이걸 루프 안에서 학생 수만큼 호출하면:
for (학생 100명) {
    INSERT INTO tb_backup SELECT ... (전체 5,000건)
}
→ 100 × 5,000 = 500,000건

-- jQuery 핸들러 5개 누적 상태에서 AJAX 5번 발사하면:
→ 5 × 500,000 = 2,500,000건

코드 한 줄이 맞아도 호출 구조가 잘못되면 데이터 폭발.
```

### 4.4 UPDATE — 고친다

```sql
-- 기본 수정
UPDATE tb_student SET std_nm = '홍길동수정' WHERE std_no = 'STD001';

-- 여러 컬럼 수정
UPDATE tb_student
SET std_nm = '홍길동수정', dept_cd = 'DEPT02', mod_dttm = NOW()
WHERE std_no = 'STD001';

-- 조건부 수정 (CASE)
UPDATE tb_exam_score
SET grade = CASE
    WHEN score >= 90 THEN 'A'
    WHEN score >= 80 THEN 'B'
    WHEN score >= 70 THEN 'C'
    ELSE 'F'
END
WHERE exam_cd = 'EXAM001';

-- 서브쿼리로 수정
UPDATE tb_student s
SET s.dept_nm = (SELECT d.dept_nm FROM tb_department d WHERE d.dept_cd = s.dept_cd);
```

!!! danger "UPDATE의 위험"
    ```sql
    -- 절대 하면 안 되는 것:
    UPDATE tb_student SET dept_cd = 'DEPT01';
    -- WHERE 절 없음 → 전체 학생의 학과가 DEPT01로 변경됨!
    ```

    **습관:**

    1. UPDATE 전에 SELECT로 대상 확인
    2. WHERE 절 반드시 작성
    3. 프로덕션에서는 트랜잭션으로 감싸기

### 4.5 DELETE — 지운다

```sql
-- 기본 삭제
DELETE FROM tb_student WHERE std_no = 'STD001';

-- 조건부 삭제
DELETE FROM tb_student WHERE dept_cd = 'DEPT99' AND reg_dttm < '2024-01-01';

-- 서브쿼리로 삭제
DELETE FROM tb_student
WHERE dept_cd IN (SELECT dept_cd FROM tb_department WHERE use_yn = 'N');
```

!!! warning "DELETE의 특징"
    1. 행을 하나씩 삭제 (WHERE 조건별)
    2. 각 행마다 Undo 로그 기록 → ROLLBACK 가능
    3. 각 행마다 트리거 발동 (있으면)
    4. 삭제 후 디스크 공간 즉시 반환 안 됨 (.ibd 파일 크기 유지)
    5. 대용량 DELETE는 Undo 로그 폭발 → 서버 부하 극심

---

## 5. DCL 상세 (Data Control Language)

### 5.1 GRANT — 권한 준다

```sql
-- 특정 DB의 모든 테이블에 SELECT 권한
GRANT SELECT ON lxpknu10.* TO 'readonly_user'@'192.168.0.%';

-- 특정 테이블에 SELECT, INSERT 권한
GRANT SELECT, INSERT ON lxpknu10.tb_student TO 'app_user'@'192.168.0.16';

-- 모든 권한 (위험!)
GRANT ALL PRIVILEGES ON lxpknu10.* TO 'admin'@'%';

-- 권한 적용
FLUSH PRIVILEGES;
```

### 5.2 REVOKE — 권한 뺏는다

```sql
-- INSERT 권한 회수
REVOKE INSERT ON lxpknu10.tb_student FROM 'app_user'@'192.168.0.16';

-- 모든 권한 회수
REVOKE ALL PRIVILEGES ON lxpknu10.* FROM 'admin'@'%';
```

### 5.3 권한 관리 원칙

!!! tip "최소 권한 원칙 (Principle of Least Privilege)"
    → 필요한 최소한의 권한만 부여
    → SELECT만 필요하면 SELECT만
    → 특정 테이블만 필요하면 특정 테이블만

    **실전 예시 (우리 서버):**

    | 계정 | 역할 |
    |------|------|
    | `lxpknu10@192.168.0.16` | WAS 서비스 계정 (SELECT, INSERT, UPDATE, DELETE) |
    | `lxpknu10@192.168.0.94` | WAS 서비스 계정 (동일) |
    | `exemone@192.168.0.88` | 외부 연동 계정 |
    | `root@localhost` | 관리자 (mysqldump 등) |

    → root를 원격에서 접속 가능하게 하면 보안 위험
    → '%'(모든 IP)에 ALL PRIVILEGES 주면 해킹당할 때 끝장

---

## 6. TCL 상세 (Transaction Control Language)

### 6.1 COMMIT — 확정한다

```sql
BEGIN;  -- 트랜잭션 시작
INSERT INTO tb_student VALUES ('STD001', '홍길동', 'DEPT01', NOW());
UPDATE tb_student SET dept_cd = 'DEPT02' WHERE std_no = 'STD002';
COMMIT;  -- 위의 INSERT, UPDATE 확정 → 영구 반영
```

### 6.2 ROLLBACK — 되돌린다

```sql
BEGIN;
DELETE FROM tb_student WHERE dept_cd = 'DEPT01';
-- "앗 잘못 지웠다!"
ROLLBACK;  -- DELETE 취소 → 원래대로 복구
```

### 6.3 SAVEPOINT — 중간 저장점

```sql
BEGIN;
INSERT INTO tb_student VALUES ('STD001', '홍길동', 'DEPT01', NOW());
SAVEPOINT sp1;  -- 여기까지 저장

INSERT INTO tb_student VALUES ('STD002', '김철수', 'DEPT02', NOW());
SAVEPOINT sp2;  -- 여기까지 저장

INSERT INTO tb_student VALUES ('STD003', '이영희', 'DEPT03', NOW());  -- 이건 잘못

ROLLBACK TO sp2;  -- STD003만 취소, STD001/STD002는 유지

COMMIT;  -- STD001, STD002 확정
```

---

## 7. DDL vs DML: 결정적 차이 총정리

| 항목 | DDL | DML |
|------|-----|-----|
| **대상** | 구조 (테이블) | 데이터 (행) |
| **Auto-Commit** | O (즉시 반영) | X (COMMIT 필요) |
| **ROLLBACK** | 불가 | 가능 (COMMIT 전) |
| **Undo 로그** | 거의 안 씀 | 씀 (복원용) |
| **Redo 로그** | 최소 | 씀 (재실행용) |
| **락 종류** | Metadata Lock | Row Lock |
| **트리거** | 발동 안 함 | 발동함 |
| **대표** | CREATE, DROP, ALTER, TRUNCATE | SELECT, INSERT, UPDATE, DELETE |

!!! danger "이 차이를 모르면 프로덕션에서 사고 친다"
    - "TRUNCATE 했는데 ROLLBACK 되겠지?" → 안 됨. 이미 끝남.
    - "ALTER TABLE 서비스 중에 해도 되겠지?" → 테이블 락 걸림.
    - "DELETE 43GB 하면 되겠지?" → Undo 로그 폭발, 서버 죽음.

---

## 8. SQL 작성 규칙 (우리 프로젝트)

### 8.1 빈 줄 금지

```sql
-- 절대 금지 (MyBatis에서 구문 에러 발생)
SELECT *
FROM tb_student

WHERE std_no = 'STD001'

-- 올바름
SELECT *
FROM tb_student
WHERE std_no = 'STD001'
```

### 8.2 MyBatis XML에서의 SQL

```xml
<!-- ExamStarePaperMapper_SQL.xml -->
<select id="listExamStarePaper" parameterType="ExamStarePaperVO" resultType="egovMap">
    /* SQL ID : listExamStarePaper */
    /* 설  명 : 시험지 목록 조회 */
    SELECT EXAM_CD
         , EXAM_QSTN_SN
         , STD_NO
         , SCORE
    FROM tb_lms_exam_stare_paper
    WHERE EXAM_CD = #{examCd}
    AND STD_NO = #{stdNo}
</select>
```

!!! danger "`#{}`와 `${}`의 차이"
    | 구문 | 동작 | 안전성 |
    |------|------|--------|
    | `#{paramName}` | PreparedStatement 바인딩 | 안전, SQL Injection 방지 |
    | `${paramName}` | 문자열 직접 치환 | 위험, SQL Injection 가능 |

    ```sql
    -- #{examCd}가 'EXAM001' 이면:
    WHERE EXAM_CD = ?  -- PreparedStatement에 'EXAM001' 바인딩 (안전)

    -- ${examCd}가 'EXAM001' 이면:
    WHERE EXAM_CD = EXAM001  -- 문자열 직접 삽입 (위험)
    -- 만약 examCd에 "'; DROP TABLE tb_student; --" 넣으면? → 테이블 삭제됨!
    ```

    **결론**: 항상 `#{}` 사용. `${}`는 ORDER BY 컬럼명 동적 처리 등 제한적으로만.

---

## 9. 핵심 정리

!!! abstract "핵심 정리"
    - **DDL** = 구조를 정의 (CREATE, ALTER, DROP, TRUNCATE) → Auto-Commit, ROLLBACK 불가 → Metadata Lock 필요
    - **DML** = 데이터를 조작 (SELECT, INSERT, UPDATE, DELETE) → 트랜잭션 내 동작, ROLLBACK 가능 → Undo/Redo 로그 기록, Row Lock
    - **DCL** = 권한 관리 (GRANT, REVOKE) → 최소 권한 원칙
    - **TCL** = 트랜잭션 제어 (COMMIT, ROLLBACK, SAVEPOINT) → DML에 대해서만 동작
    - **핵심**: DDL은 되돌릴 수 없다. DML은 COMMIT 전에 되돌린다. 이 차이 하나가 43GB 데이터를 살릴 수도, 죽일 수도 있다.
    - **다음 장**: DELETE / TRUNCATE / DROP 상세 비교 → "43GB를 어떻게 지워야 서버가 안 죽는지"
