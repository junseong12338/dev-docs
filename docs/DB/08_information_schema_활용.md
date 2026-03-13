# 08. information_schema 활용 -- DB의 X-ray

---

## 1. information_schema란?

### 1.1 한 문장 정의

**"DB 자신에 대한 정보를 담고 있는 가상 데이터베이스."**

병원에서 MRI를 찍으면 몸 내부를 볼 수 있다.
information_schema는 DB의 MRI다. DB 안에 어떤 테이블이 있고, 각각 몇 건이고, 인덱스는 뭐가 걸려 있고, 지금 누가 뭘 하고 있는지 전부 보여준다.

### 1.2 왜 알아야 하는가

!!! tip "왜 알아야 하는가"
    상황: 서버가 느려졌다. 디스크가 부족하다. 뭔가 멈춰 있다.

    | 행동 | 레벨 |
    |------|------|
    | "서버가 느려요" 라고 보고한다 | Lv1 병아리 |
    | 어떤 테이블이 큰지 조회한다 | Lv2 새싹 |
    | 원인 테이블을 찾고 왜 큰지 분석한다 | Lv3 주니어 |
    | 열려있는 트랜잭션까지 특정한다 | Lv4 시니어 |

    information_schema를 모르면 Lv2도 못 한다.

### 1.3 가상 뷰라는 것의 의미

!!! note "가상 뷰라는 것의 의미"
    | 구분 | 일반 테이블 | information_schema |
    |------|-----------|-------------------|
    | 저장 | 실제 디스크에 .ibd 파일 | 디스크에 파일 없음 |
    | 데이터 | 물리적 저장 | 조회 시점에 메타데이터 수집 |
    | 수정 | INSERT/UPDATE/DELETE 가능 | 읽기 전용 |

    ```sql
    USE information_schema;   -- 이렇게 접속해서
    SELECT * FROM TABLES;     -- 이렇게 조회한다
    ```

---

## 2. 주요 테이블 상세

| 테이블 | 무엇을 보여주나 |
|--------|----------------|
| **TABLES** | 테이블 이름, 행 수, 용량, 엔진 |
| **COLUMNS** | 컬럼 이름, 타입, NULL 허용, 기본값 |
| **STATISTICS** | 인덱스 이름, 대상 컬럼, 카디널리티 |
| **INNODB_TRX** | 열려있는 InnoDB 트랜잭션 |
| **PROCESSLIST** | 현재 접속 세션, 실행 중인 쿼리 |
| **INNODB_LOCK_WAITS** | 누가 누구의 락을 기다리는지 |
| **KEY_COLUMN_USAGE** | PK, FK 관계 |
| **SCHEMATA** | 데이터베이스 목록 |

!!! tip ""
    "이것만 알면 DB 상태의 80%는 파악할 수 있다."

---

### 2.1 TABLES -- 테이블 정보의 핵심

**역할**: DB 안의 모든 테이블에 대한 메타 정보. 용량, 행 수, 엔진, 생성일 등.

**주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| **TABLE_SCHEMA** | 데이터베이스 이름 |
| **TABLE_NAME** | 테이블 이름 |
| **ENGINE** | 스토리지 엔진 (InnoDB, MyISAM 등) |
| **TABLE_ROWS** | 행 수 (InnoDB: 추정치!) |
| **DATA_LENGTH** | 데이터 크기 (바이트) |
| **INDEX_LENGTH** | 인덱스 크기 (바이트) |
| **DATA_FREE** | 사용 가능한 빈 공간 (바이트) |
| **CREATE_TIME** | 테이블 생성 시간 |
| **UPDATE_TIME** | 마지막 수정 시간 |
| **TABLE_COMMENT** | 테이블 코멘트 |

**기본 용량 확인 쿼리:**

```sql
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_mb,
    ROUND(INDEX_LENGTH / 1024 / 1024, 2) AS index_mb,
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2) AS total_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_database'
ORDER BY DATA_LENGTH DESC;
```

**GB 단위가 필요하면:**

```sql
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024 / 1024, 2) AS data_gb,
    ROUND(INDEX_LENGTH / 1024 / 1024 / 1024, 2) AS index_gb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_database'
  AND DATA_LENGTH > 1024 * 1024 * 1024   -- 1GB 이상만
ORDER BY DATA_LENGTH DESC;
```

**TABLE_ROWS는 정확한 값이 아니다:**

!!! warning "TABLE_ROWS는 정확한 값이 아니다"
    InnoDB의 TABLE_ROWS는 "추정치"다. 정확하지 않다.

    **왜?**

    - InnoDB는 MVCC를 써서 각 트랜잭션마다 보이는 행이 다를 수 있다
    - 정확한 카운트를 유지하지 않고 통계적 샘플링으로 추정한다

    | 방법 | 정확도 | 속도 |
    |------|--------|------|
    | `TABLE_ROWS` | 대략 이 정도 | 빠름, 부하 없음 |
    | `COUNT(*)` | 정확히 이 만큼 | 느림, 부하 있음 (2.7억 건 = 27분) |

    → 상황에 따라 골라 써라

**TRUNCATE 후 확인하는 패턴:**

```sql
-- TRUNCATE 실행 후 진짜 비워졌는지 확인
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024, 2) AS data_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_database'
  AND TABLE_NAME = 'tb_lms_exam_stare_paper_backup';

-- 결과:
-- TABLE_ROWS: 0
-- data_mb: 0.02
-- → .ibd 파일이 재생성되어 거의 빈 상태
```

---

### 2.2 COLUMNS -- 컬럼 정보

**역할**: 테이블의 컬럼 구조를 조회. DESC 테이블명과 비슷하지만 SQL로 필터링 가능.

**주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| **TABLE_NAME** | 테이블 이름 |
| **COLUMN_NAME** | 컬럼 이름 |
| **ORDINAL_POSITION** | 컬럼 순서 (1부터) |
| **COLUMN_DEFAULT** | 기본값 |
| **IS_NULLABLE** | NULL 허용 여부 (YES/NO) |
| **DATA_TYPE** | 데이터 타입 (varchar, int, datetime 등) |
| **CHARACTER_MAXIMUM_LENGTH** | 문자열 최대 길이 |
| **COLUMN_KEY** | 키 정보 (PRI, UNI, MUL) |
| **EXTRA** | auto_increment 등 추가 정보 |

**사용 예시:**

```sql
-- 특정 테이블의 전체 컬럼 구조
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH AS max_len,
    IS_NULLABLE,
    COLUMN_KEY,
    COLUMN_DEFAULT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'your_database'
  AND TABLE_NAME = 'tb_lms_exam_stare_paper_backup'
ORDER BY ORDINAL_POSITION;
```

```sql
-- 특정 컬럼 이름이 어떤 테이블에 있는지 찾기
-- "exam_cd라는 컬럼이 어디어디에 있지?"
SELECT
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'your_database'
  AND COLUMN_NAME LIKE '%exam_cd%';
```

!!! tip "왜 COLUMNS가 유용한가"
    | 방법 | 범위 |
    |------|------|
    | `DESC 테이블명;` | 한 테이블만 |
    | `information_schema.COLUMNS` | 전체 DB에서 검색 가능 |

    레거시 시스템에서 "이 컬럼이 어디서 쓰이지?" 할 때 핵심.
    LXP-KNU10처럼 테이블이 수백 개면, 일일이 DESC 칠 수 없다.

---

### 2.3 STATISTICS -- 인덱스 정보

**역할**: 테이블에 걸려 있는 인덱스 정보를 조회.

**주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| **TABLE_NAME** | 테이블 이름 |
| **INDEX_NAME** | 인덱스 이름 (PRIMARY = PK) |
| **SEQ_IN_INDEX** | 복합 인덱스에서의 순서 |
| **COLUMN_NAME** | 인덱스 대상 컬럼 |
| **NON_UNIQUE** | 0 = UNIQUE, 1 = 중복 허용 |
| **CARDINALITY** | 고유값 수 (추정치, 인덱스 효율 판단 기준) |
| **INDEX_TYPE** | BTREE, FULLTEXT, HASH 등 |

**사용 예시:**

```sql
-- 특정 테이블의 인덱스 확인
SELECT
    INDEX_NAME,
    SEQ_IN_INDEX,
    COLUMN_NAME,
    NON_UNIQUE,
    CARDINALITY,
    INDEX_TYPE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'your_database'
  AND TABLE_NAME = 'tb_lms_exam_stare_paper_backup'
ORDER BY INDEX_NAME, SEQ_IN_INDEX;

-- 결과가 비어 있다면?
-- → 인덱스가 하나도 없다
-- → 2.7억 건에 인덱스 없으면 모든 조회가 풀스캔
-- → 이게 바로 COUNT(*) 27분의 원인
```

```sql
-- 인덱스 없는 테이블 찾기
-- (PK조차 없는 테이블 = 위험)
SELECT t.TABLE_NAME, t.TABLE_ROWS
FROM information_schema.TABLES t
LEFT JOIN information_schema.STATISTICS s
  ON t.TABLE_SCHEMA = s.TABLE_SCHEMA
  AND t.TABLE_NAME = s.TABLE_NAME
WHERE t.TABLE_SCHEMA = 'your_database'
  AND t.TABLE_ROWS > 10000
  AND s.INDEX_NAME IS NULL
ORDER BY t.TABLE_ROWS DESC;
```

!!! note "CARDINALITY란?"
    해당 인덱스 컬럼의 고유값 수.

    | 예시 | 카디널리티 |
    |------|-----------|
    | 성별 컬럼 | 2 (M, F) |
    | 사용자ID | 100만 (100만 명) |

    카디널리티가 높을수록 인덱스 효율이 좋다.
    카디널리티가 낮으면 인덱스 걸어봤자 효과 미미.
    → 이건 09장(인덱스 완전정복)에서 깊이 다룬다.

---

### 2.4 INNODB_TRX -- 열려있는 트랜잭션

**역할**: 현재 InnoDB에서 실행 중인(열려 있는) 트랜잭션 정보.

이것이 왜 중요하냐.

!!! danger "범인 찾기"
    TRUNCATE TABLE을 실행했는데 멈춰 있다.
    "Waiting for table metadata lock" 상태.
    누군가가 해당 테이블을 쓰고 있어서 metadata lock이 안 풀린다.

    범인을 찾으려면? → **INNODB_TRX를 본다.**

**주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| **trx_id** | 트랜잭션 ID |
| **trx_state** | 상태 (RUNNING, LOCK WAIT 등) |
| **trx_started** | 트랜잭션 시작 시간 |
| **trx_mysql_thread_id** | MySQL 스레드 ID (= SHOW PROCESSLIST의 Id) |
| **trx_query** | 현재 실행 중인 쿼리 (NULL일 수 있음) |
| **trx_tables_locked** | 락 걸린 테이블 수 |
| **trx_rows_locked** | 락 걸린 행 수 |
| **trx_rows_modified** | 수정된 행 수 |

**핵심 포인트: trx_mysql_thread_id**

!!! danger "핵심 포인트: trx_mysql_thread_id"
    `INNODB_TRX.trx_mysql_thread_id` = `SHOW PROCESSLIST`의 `Id`

    INNODB_TRX에서 범인 트랜잭션을 찾았다
    → trx_mysql_thread_id가 12345
    → SHOW PROCESSLIST에서 Id=12345를 찾으면
    → 어떤 사용자(User), 어떤 호스트(Host), 어떤 DB에서 접속했는지 알 수 있다
    → `KILL 12345;` 로 해당 세션을 종료할 수 있다

    **이 연결고리를 모르면 범인을 찾아도 처리를 못 한다.**

**사용 예시:**

```sql
-- 열려있는 트랜잭션 전부 조회
SELECT
    trx_id,
    trx_state,
    trx_started,
    TIMESTAMPDIFF(SECOND, trx_started, NOW()) AS duration_sec,
    trx_mysql_thread_id,
    trx_query,
    trx_tables_locked,
    trx_rows_locked,
    trx_rows_modified
FROM information_schema.INNODB_TRX
ORDER BY trx_started;

-- 10분 이상 열려있는 트랜잭션 (위험)
SELECT
    trx_id,
    trx_state,
    trx_started,
    TIMESTAMPDIFF(MINUTE, trx_started, NOW()) AS duration_min,
    trx_mysql_thread_id,
    trx_query
FROM information_schema.INNODB_TRX
WHERE TIMESTAMPDIFF(MINUTE, trx_started, NOW()) > 10;
```

**trx_query가 NULL인 경우:**

!!! danger "trx_query가 NULL인 경우"
    trx_query가 NULL이라고 "아무것도 안 하고 있다"는 게 아니다.

    트랜잭션은 열려 있지만 현재 쿼리를 실행하고 있지 않은 상태.
    예: BEGIN 후 SELECT 하고 결과를 보고 있는 중
    → 트랜잭션은 열려 있지만 실행 중인 쿼리는 없다
    → **이 상태에서도 락은 유지되고 있다!**

    이런 놈이 제일 무서운 범인이다.
    겉으로 보면 조용한데, 안에서는 락을 잡고 안 놓고 있다.

---

### 2.5 PROCESSLIST -- 프로세스 목록

**역할**: 현재 MySQL/MariaDB에 접속해 있는 모든 세션 정보.

!!! tip "SHOW PROCESSLIST vs information_schema.PROCESSLIST"
    | 기능 | SHOW PROCESSLIST | information_schema.PROCESSLIST |
    |------|-----------------|-------------------------------|
    | WHERE 필터링 | X | O |
    | ORDER BY 정렬 | X | O |
    | JOIN 결합 | X | O |

**주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| **ID** | 세션 ID (KILL로 종료할 때 사용) |
| **USER** | 접속 사용자 |
| **HOST** | 접속 호스트 (IP:포트) |
| **DB** | 사용 중인 데이터베이스 |
| **COMMAND** | 현재 상태 (Query, Sleep, Connect 등) |
| **TIME** | 현재 상태 유지 시간 (초) |
| **STATE** | 상세 상태 |
| **INFO** | 실행 중인 쿼리 |

**사용 예시:**

```sql
-- 현재 실행 중인 쿼리만 보기 (Sleep 제외)
SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO
FROM information_schema.PROCESSLIST
WHERE COMMAND != 'Sleep'
ORDER BY TIME DESC;

-- metadata lock 걸린 세션 찾기
SELECT ID, USER, HOST, DB, COMMAND, TIME, STATE, INFO
FROM information_schema.PROCESSLIST
WHERE STATE LIKE '%metadata lock%';
```

---

### 2.6 INNODB_LOCK_WAITS -- 락 대기 관계

**역할**: "누가 누구 때문에 기다리고 있는지" 관계를 보여준다.

!!! note "INNODB_LOCK_WAITS의 역할"
    - 세션 A가 행을 수정 중 (락 보유)
    - 세션 B가 같은 행을 수정하려고 대기 중
    - INNODB_LOCK_WAITS는 이 관계를 보여준다: "세션 B는 세션 A의 락 때문에 대기 중"

**주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| **requesting_trx_id** | 기다리고 있는 트랜잭션 ID (피해자) |
| **blocking_trx_id** | 막고 있는 트랜잭션 ID (범인) |
| **requesting_lock_id** | 요청 중인 락 ID |
| **blocking_lock_id** | 차단 중인 락 ID |

**사용 예시:**

```sql
-- 락 대기 관계 조회 (누가 누구를 막고 있나)
SELECT
    w.requesting_trx_id AS waiting_trx,
    w.blocking_trx_id AS blocking_trx,
    r.trx_mysql_thread_id AS waiting_thread,
    b.trx_mysql_thread_id AS blocking_thread,
    r.trx_query AS waiting_query,
    b.trx_query AS blocking_query,
    b.trx_started AS blocking_since
FROM information_schema.INNODB_LOCK_WAITS w
JOIN information_schema.INNODB_TRX r
  ON w.requesting_trx_id = r.trx_id
JOIN information_schema.INNODB_TRX b
  ON w.blocking_trx_id = b.trx_id;
```

!!! tip "결과 읽는 법"
    | 컬럼 | 의미 |
    |------|------|
    | `blocking_thread` | 범인의 스레드 ID |
    | `waiting_thread` | 피해자의 스레드 ID |
    | `blocking_query` | 범인이 실행 중인 쿼리 (NULL이면 idle 상태) |
    | `blocking_since` | 범인이 트랜잭션 시작한 시간 |

    → 범인 특정 후 `KILL blocking_thread;` 로 해결
    → 물론 KILL 전에 왜 그 트랜잭션이 열려 있는지 파악해야 한다

---

## 3. 실전 쿼리 레시피

### 3.1 테이블별 용량 TOP 10

```sql
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024 / 1024, 2) AS data_gb,
    ROUND(INDEX_LENGTH / 1024 / 1024 / 1024, 2) AS index_gb,
    ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024 / 1024, 2) AS total_gb,
    ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_database'
ORDER BY (DATA_LENGTH + INDEX_LENGTH) DESC
LIMIT 10;
```

!!! tip "이 쿼리를 가장 먼저 치는 이유"
    - 디스크 부족? → 누가 차지하고 있는지 먼저 본다
    - 서버 느려? → 큰 테이블이 보통 범인이다
    - 마이그레이션? → 용량을 알아야 시간 산정이 된다

    우리 사례에서 이 쿼리를 쳤더니:
    tb_lms_exam_stare_paper_backup → 43GB, 2.7억 건
    → 전체 디스크의 22%를 이 테이블 하나가 차지

### 3.2 특정 테이블 인덱스 확인

```sql
SELECT
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns,
    NON_UNIQUE,
    INDEX_TYPE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = 'your_database'
  AND TABLE_NAME = 'tb_lms_exam_stare_paper_backup'
GROUP BY INDEX_NAME, NON_UNIQUE, INDEX_TYPE;
```

!!! note "GROUP_CONCAT을 쓰는 이유"
    복합 인덱스(A, B, C)는 3행으로 나온다.

    GROUP_CONCAT으로 묶으면: `INDEX_NAME: idx_abc, columns: A,B,C` → 한눈에 보인다

### 3.3 열려있는 트랜잭션 확인

```sql
SELECT
    t.trx_id,
    t.trx_state,
    t.trx_started,
    TIMESTAMPDIFF(SECOND, t.trx_started, NOW()) AS duration_sec,
    t.trx_mysql_thread_id,
    t.trx_query,
    p.USER,
    p.HOST,
    p.DB
FROM information_schema.INNODB_TRX t
JOIN information_schema.PROCESSLIST p
  ON t.trx_mysql_thread_id = p.ID
ORDER BY t.trx_started;
```

!!! tip "INNODB_TRX와 PROCESSLIST를 JOIN하는 이유"
    INNODB_TRX만으로는 "누가" 열었는지 모른다
    → `trx_mysql_thread_id`로 PROCESSLIST와 연결
    → USER, HOST, DB까지 확인 가능

    "아, 배치 서버(192.168.1.50)의 backup_user가 30분째 트랜잭션을 안 닫고 있구나"
    → 이 정도까지 파악해야 한다

### 3.4 오래된 Sleep 세션 찾기

```sql
SELECT ID, USER, HOST, DB, COMMAND, TIME,
    ROUND(TIME / 60, 1) AS minutes
FROM information_schema.PROCESSLIST
WHERE COMMAND = 'Sleep'
  AND TIME > 300   -- 5분 이상 Sleep
ORDER BY TIME DESC;
```

!!! danger "Sleep 세션이 왜 문제인가"
    Sleep = 연결은 맺고 있지만 아무 쿼리도 안 하는 상태

    - 연결 풀을 차지한다
    - max_connections에 카운트된다
    - 너무 많으면 새 연결이 거부된다

    **근데 더 무서운 건:**
    Sleep이면서 트랜잭션이 열려 있는 경우
    → INNODB_TRX에 나타난다
    → 락을 잡고 있을 수 있다
    → 겉으로는 조용한데 안에서는 테러범

### 3.5 테이블별 행 수 확인

```sql
-- 추정치 (빠름, 부하 없음)
SELECT
    TABLE_NAME,
    TABLE_ROWS,
    ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'your_database'
  AND TABLE_ROWS > 0
ORDER BY TABLE_ROWS DESC;
```

!!! note "다시 강조: TABLE_ROWS는 추정치"
    실제 값과 10~20% 차이 날 수 있다.
    하지만 "어떤 테이블이 큰지" 순위를 보는 데는 충분하다.

    정확한 값이 필요한 상황: 마이그레이션 검증, 법적 보고 → 이럴 때만 COUNT(*) 쓴다

---

## 4. 우리 사례에 대입

### 4.1 TRUNCATE 후 확인

```sql
-- TRUNCATE 전
SELECT TABLE_NAME, TABLE_ROWS,
    ROUND(DATA_LENGTH / 1024 / 1024 / 1024, 2) AS data_gb
FROM information_schema.TABLES
WHERE TABLE_NAME = 'tb_lms_exam_stare_paper_backup';

-- 결과:
-- TABLE_ROWS: 270000000 (추정치)
-- data_gb: 43.17

-- TRUNCATE 후
-- TABLE_ROWS: 0
-- data_gb: 0.00
-- → 43GB가 0으로. .ibd 파일이 재생성됨.
```

### 4.2 INNODB_TRX로 범인 특정

!!! danger "실제 있었던 일"
    TRUNCATE TABLE 실행 → "Waiting for table metadata lock" 상태로 멈춤 → 10분, 20분... 안 끝남

    **왜?** 누군가가 이 테이블에 대해 트랜잭션을 열고 안 닫았다. TRUNCATE는 DDL이라 metadata lock이 필요하고, metadata lock을 얻으려면 모든 트랜잭션이 끝나야 한다.

    **찾는 방법:**

```sql
-- Step 1: INNODB_TRX 확인
SELECT trx_id, trx_state, trx_started,
    trx_mysql_thread_id, trx_query
FROM information_schema.INNODB_TRX;

-- Step 2: 범인 스레드를 PROCESSLIST에서 확인
SELECT ID, USER, HOST, DB, COMMAND, TIME, INFO
FROM information_schema.PROCESSLIST
WHERE ID = [범인_thread_id];

-- Step 3: 확인 후 KILL
KILL [범인_thread_id];

-- Step 4: TRUNCATE 재실행 → 성공
```

### 4.3 MariaDB 버전이 낮아 생긴 문제

!!! warning "MariaDB 버전에 따른 차이"
    | 버전 | metadata_locks | 진단 방법 |
    |------|---------------|-----------|
    | MariaDB 10.5+ | `performance_schema.metadata_locks` 있음 | 직접 조회 가능 |
    | MariaDB 10.3 이하 | 없음 | INNODB_TRX + PROCESSLIST 조합으로 우회 |

    우리 서버는 MariaDB 10.3이었다.
    → metadata_locks 조회 불가
    → INNODB_TRX에서 시간대 기반으로 범인 추정
    → SHOW PROCESSLIST의 State로 확인
    → 해당 테이블을 쓰고 있을 법한 트랜잭션을 특정

    **교훈:** 도구가 없으면 우회한다. 하지만 도구가 있으면 쓴다. 버전 업그레이드할 때 이런 진단 기능도 고려해야 한다.

---

## 5. 핵심 정리

!!! abstract "08장 핵심 정리: information_schema"
    1. **information_schema는 DB의 X-ray다** → DB 구조, 용량, 인덱스, 트랜잭션, 세션 전부 조회 가능. 가상 뷰이므로 읽기 전용, 디스크 파일 없음.
    2. **핵심 테이블 6개** → TABLES(용량, 행 수 - TABLE_ROWS는 추정치!), COLUMNS(컬럼 구조), STATISTICS(인덱스 정보 - 없으면 풀스캔), INNODB_TRX(열려있는 트랜잭션 - 범인 찾기), PROCESSLIST(현재 세션 - WHO/WHERE/WHAT), INNODB_LOCK_WAITS(락 대기 관계 - 누가 누구를 막나)
    3. **trx_mysql_thread_id = PROCESSLIST.ID** → 이 연결고리가 범인 특정의 핵심. 트랜잭션 찾고 → 세션 찾고 → KILL로 해결.
    4. **TABLE_ROWS는 추정치다** → 순위 보기에는 충분, 정확한 값은 COUNT(*). 2.7억 건에 COUNT(*) = 27분 (인덱스 없을 때).
    5. **버전에 따라 사용 가능한 테이블이 다르다** → MariaDB 10.3: metadata_locks 없음. MariaDB 10.5+: performance_schema.metadata_locks 있음.

    "DB 문제가 터졌을 때 information_schema를 못 쓰면 눈 감고 수술하는 거야. 기본 중의 기본이다."

**다음 장에서 배울 것:** 09장에서는 인덱스를 완전 정복한다. information_schema.STATISTICS에서 인덱스가 "없다"는 걸 확인했으면, 이제 "왜 없으면 안 되는지", "어떻게 동작하는지", "언제 걸고 언제 안 거는지"를 배운다. 2.7억 건에 COUNT(*) 27분이 걸리는 근본 원인을 이해하게 된다.
