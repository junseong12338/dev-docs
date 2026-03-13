# 11. mysqldump와 백업 전략

---

## 1. 백업이 왜 필요한가

### 1.1 데이터는 언제든 사라진다

!!! danger "데이터가 날아가는 4가지 경로"
    1. **하드웨어 장애** -- HDD/SSD는 기계다. 기계는 언젠가 죽는다. MTBF(평균 고장 간격)가 100만 시간이라고? 서버 100대면 매달 1대씩 죽는다는 소리야.
    2. **인간의 실수** -- WHERE 빠진 DELETE(전체 삭제), DROP TABLE 오타(테이블 증발), UPDATE SET password = '1234' WHERE 안 써서 전체 변경. "아 실수로요" -- 그 실수가 서비스를 끝낸다.
    3. **악의적 공격** -- 랜섬웨어(데이터 암호화 후 몸값 요구), SQL Injection(외부에서 DROP TABLE 실행), 내부자 위협(퇴사 직전 삭제).
    4. **소프트웨어 버그** -- 우리 프로젝트가 바로 이 경우. jQuery 이벤트 중복 → AJAX N배 증폭 → 2.7억 건 축적. 코드 버그 하나가 43GB 테이블을 만들었다.

### 1.2 백업 없으면 뭐가 일어나?

!!! danger "백업 없이 데이터 날아감"
    - 복구 불가
    - 사용자 데이터 전부 소실
    - 서비스 신뢰도 0
    - 법적 책임 (개인정보보호법 위반 가능)
    - 서비스 종료

    "14개월간 백업이 0바이트였습니다"

    - 그 14개월 동안 서버가 죽었으면?
    - 모든 학습 데이터, 성적, 수강 기록 전부 소멸.
    - 끝.

백업은 보험이다. 보험료(디스크 비용, 시간)를 안 내면 사고 났을 때 전부 잃는다.

**왜 14개월간 아무도 몰랐을까?**

백업 스크립트는 돌았다. crontab에 등록되어 있으니까 매일 00:00에 실행됐다.
그런데 **결과를 아무도 확인 안 했다.**
파일이 만들어졌는데 크기가 0바이트인 걸 아무도 안 봤다.

**교훈: 백업은 "실행"이 아니라 "검증"까지 해야 완성이다.**

---

## 2. 백업의 종류

### 2.1 논리 백업 (Logical Backup)

!!! note "논리 백업 = 데이터를 SQL 문장으로 내보내기"
    **비유:** 책의 내용을 손으로 전부 필사하는 것. 느리지만, 어떤 종이(다른 DBMS)에든 옮길 수 있다. 사람이 읽을 수 있다 (텍스트 파일).

    **대표 도구:** mysqldump

    **작동 방식:** DB에 접속 → 테이블 구조를 CREATE TABLE 문으로 추출 → 데이터를 INSERT INTO 문으로 추출 → .sql 파일로 저장

    | 구분 | 내용 |
    |------|------|
    | 장점 | 이식성 (다른 DBMS 이관 가능), 가독성 (텍스트), 선택적 백업 가능, 버전 무관 |
    | 단점 | 느림 (SQL 파싱), 복원 느림 (INSERT 한 줄씩), 대용량 한계 (43GB → 덤프만 20분), 덤프 파일이 원본보다 클 수 있음 |

### 2.2 물리 백업 (Physical Backup)

!!! note "물리 백업 = 데이터 파일 자체를 통째로 복사"
    **비유:** 책 전체를 복사기로 복사하는 것. 빠르지만, 같은 크기의 종이(같은 DBMS)에서만 읽을 수 있다.

    **대표 도구:** Percona XtraBackup, MariaDB Mariabackup

    **작동 방식:** InnoDB 데이터 파일(.ibd)을 직접 복사 → 복사 중 발생한 변경을 redo 로그로 따라잡기 → 바이너리 파일 그대로 보관

    | 구분 | 내용 |
    |------|------|
    | 장점 | 빠름 (파일 복사), 복원 빠름 (파일 배치), Hot Backup 가능 |
    | 단점 | 이식성 없음 (같은 DBMS만), 불투명 (바이너리), 전체만 가능, 설정 의존 |

### 2.3 비교표

| 항목 | 논리 백업 (mysqldump) | 물리 백업 (xtrabackup) |
|------|----------------------|----------------------|
| 백업 속도 | 느림 (SQL 생성) | 빠름 (파일 복사) |
| 복원 속도 | 느림 (SQL 실행) | 빠름 (파일 배치) |
| 이식성 | 높음 (다른 DBMS 가능) | 낮음 (같은 DBMS만) |
| 사람이 읽을 수 | 가능 (텍스트) | 불가 (바이너리) |
| 선택적 백업 | 가능 (테이블/조건) | 제한적 |
| 서비스 영향 | --single-transaction 쓰면 최소화 | Hot Backup 가능 |
| 디스크 사용 | 원본보다 클 수 있음 | 원본과 비슷 |
| 백업 중 락 | InnoDB면 없음 (--single-transaction) | 없음 |
| 적합한 상황 | 소규모~중규모 DB, 이관, 부분 복원 | 대규모 DB, 전체 복원, DR |

### 2.4 우리 서버는 왜 mysqldump를 쓰나?

!!! example "우리 서버가 mysqldump를 쓰는 이유"
    **서버:** knuLMS-DB01 / **DB 크기:** 약 50GB (문제 테이블 제거 전) → 약 7GB (제거 후)

    **선택 이유:** DB 규모가 크지 않다 (정상 상태에서 ~7GB), 별도 도구 설치 불필요 (MariaDB에 내장), 설정이 단순하다, 복원 시 SQL이라서 디버깅 가능.

    **문제:** 43GB 테이블이 끼면서 mysqldump 출력이 73GB 예상 → 196GB 디스크에 134GB 사용 중 → 여유 53GB → 73GB > 53GB → Disk Full → 0바이트 파일 생성.

---

## 3. mysqldump 상세

### 3.1 기본 사용법

```bash
# 기본 형태
mysqldump -u [사용자] -p[비밀번호] [데이터베이스명] > [출력파일.sql]

# 예시: lxpknu10 데이터베이스 전체 백업
mysqldump -u root -p'MyP@ss!' lxpknu10 > /backup/lxpknu10_backup.sql

# 특정 테이블만
mysqldump -u root -p'MyP@ss!' lxpknu10 tb_user tb_course > /backup/partial.sql

# 여러 데이터베이스
mysqldump -u root -p'MyP@ss!' --databases lxpknu10 lxpknu9 > /backup/multi.sql

# 전체 (모든 데이터베이스)
mysqldump -u root -p'MyP@ss!' --all-databases > /backup/all.sql
```

**주의: `-p`와 비밀번호 사이에 공백 없음!**

```bash
# 올바름
mysqldump -u root -p'MyP@ss!' lxpknu10

# 틀림 (비밀번호를 DB명으로 인식)
mysqldump -u root -p 'MyP@ss!' lxpknu10
```

### 3.2 주요 옵션 전부 설명

#### --single-transaction (핵심 중의 핵심)

!!! tip "--single-transaction (핵심 중의 핵심)"
    **용도:** 백업 중에도 서비스 정상 운영. **동작:** InnoDB의 MVCC를 이용해 스냅샷 시점 기준으로 읽기. **효과:** 테이블 락 없이 일관된 백업.

    ```bash
    mysqldump --single-transaction -u root -p'pass' lxpknu10
    ```

    이 옵션 안 쓰면? 테이블마다 READ LOCK 걸림 → 백업 중 INSERT/UPDATE 전부 대기 → 서비스 먹통. InnoDB 테이블에서만 의미 있음. MyISAM은 어차피 테이블 락 필수.

#### --routines / -R (스토어드 프로시저/함수)

!!! warning "--routines / -R (스토어드 프로시저/함수)"
    **용도:** 스토어드 프로시저, 함수를 백업에 포함. **기본값: 포함 안 됨!**

    ```bash
    mysqldump --single-transaction --routines -u root -p'pass' lxpknu10
    ```

    이거 빠뜨리면? 복원 후 프로시저/함수 전부 없음 → 프로시저 호출하는 코드 전부 에러 → "복원했는데 왜 안 돼요?" ← 이거.

#### --triggers

!!! note "--triggers"
    **용도:** 트리거를 백업에 포함. **기본값:** 포함됨 (기본 ON). 안심하지 마. 명시적으로 쓰는 습관 들여.

    ```bash
    mysqldump --single-transaction --routines --triggers -u root -p'pass' lxpknu10
    ```

#### --ignore-table (테이블 제외)

!!! tip "--ignore-table (테이블 제외)"
    **용도:** 특정 테이블을 백업에서 제외. **형식:** `--ignore-table=DB명.테이블명` (점으로 구분)

    ```bash
    # 43GB짜리 테이블 제외
    mysqldump --single-transaction \
      --ignore-table=lxpknu10.tb_lms_exam_stare_paper_backup \
      -u root -p'pass' lxpknu10

    # 여러 개 제외
    mysqldump --single-transaction \
      --ignore-table=lxpknu10.tb_log_access \
      --ignore-table=lxpknu10.tb_log_error \
      -u root -p'pass' lxpknu10
    ```

    이 옵션 하나가 우리 백업을 살렸다. 73GB → 약 10GB (43GB 테이블 제외) → Disk Full 해결 → 14개월간의 백업 실패 종료.

#### --where (조건부 백업)

!!! note "--where (조건부 백업)"
    **용도:** 특정 조건의 데이터만 백업. **형식:** `--where="SQL 조건"`

    ```bash
    # 최근 30일 로그만
    mysqldump --single-transaction \
      --where="created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)" \
      -u root -p'pass' lxpknu10 tb_log

    # 특정 사용자만
    mysqldump --single-transaction \
      --where="user_no = '12345'" \
      -u root -p'pass' lxpknu10 tb_user
    ```

#### --no-data / -d (구조만)

!!! note "--no-data / -d (구조만)"
    **용도:** 테이블 구조(DDL)만 백업, 데이터 제외. **활용:** 스키마 이관, 테이블 구조 비교.

    ```bash
    mysqldump --no-data -u root -p'pass' lxpknu10 > schema_only.sql
    ```

    43GB 테이블도 구조만 뽑으면 몇 KB.

#### --databases vs 스키마 직접 지정

```bash
# --databases: USE 문 + CREATE DATABASE 포함
mysqldump --databases lxpknu10 -u root -p'pass' > with_create_db.sql
# 출력에 포함되는 것:
#   CREATE DATABASE lxpknu10;
#   USE lxpknu10;
#   CREATE TABLE ...

# 스키마 직접 지정: USE 문 없음
mysqldump lxpknu10 -u root -p'pass' > without_create_db.sql
# 출력에 포함되는 것:
#   CREATE TABLE ...

차이가 왜 중요해?
→ 다른 이름의 DB로 복원하고 싶을 때
→ --databases 쓰면 원래 이름으로만 복원됨
→ 직접 지정하면 원하는 DB에 복원 가능
```

#### --lock-tables vs --single-transaction

| 구분 | --lock-tables | --single-transaction |
|------|---------------|----------------------|
| 방식 | 테이블별 READ LOCK | InnoDB MVCC 스냅샷 |
| 대상 | MyISAM용 | InnoDB용 |
| 쓰기 | 백업 중 쓰기 차단 | 백업 중 쓰기 가능 |
| 일관성 | 테이블 단위 | 전체 DB 수준 |
| 서비스 영향 | 큼 | 거의 없음 |

!!! warning "InnoDB 서버라면"
    우리 서버는 InnoDB니까 --single-transaction 필수.
    --lock-tables 쓰면 00:00에 백업 시작하고
    백업 끝날 때까지 모든 쓰기가 멈춘다.

#### --quick (대용량 필수)

!!! note "--quick (대용량 필수)"
    **용도:** 한 행씩 바로 출력 (메모리에 전체 적재 안 함). **기본값:** mysqldump에서 기본 활성화됨.

    | 모드 | 동작 |
    |------|------|
    | --quick 없이 | 테이블 전체를 메모리에 올린 후 출력 |
    | --quick 있으면 | 한 행 읽고 바로 출력, 한 행 읽고 바로 출력 |

    43GB 테이블을 메모리에 올리면? → OOM(Out of Memory) → 서버 죽음. 기본 활성화라서 보통 안 써도 되지만, 대용량 테이블 있으면 명시적으로 확인하는 습관.

#### --compress

!!! note "--compress"
    **용도:** 클라이언트-서버 간 네트워크 전송 시 압축. **주의:** 출력 파일 압축이 아님! 네트워크 전송 압축.

    ```bash
    # 원격 서버에서 백업할 때
    mysqldump --compress -h remote-server -u root -p'pass' lxpknu10 > backup.sql

    # 출력 파일 압축은 파이프로
    mysqldump -u root -p'pass' lxpknu10 | gzip > backup.sql.gz
    ```

### 3.3 --single-transaction 원리

이 옵션이 뭘 하는지 "대충 안다"는 건 Lv2야. 원리를 알아야 Lv4.

!!! note "--single-transaction 동작 순서"
    1. `SET SESSION TRANSACTION ISOLATION LEVEL REPEATABLE READ`
        - 격리 수준을 REPEATABLE READ로 설정

    2. `START TRANSACTION WITH CONSISTENT SNAPSHOT`
        - 이 시점의 DB 스냅샷을 생성
        - 이후 다른 트랜잭션이 INSERT/UPDATE 해도 이 스냅샷에는 안 보임 (MVCC)

    3. 각 테이블을 순차적으로 SELECT → 파일에 기록
        - 스냅샷 시점 기준 데이터만 읽음
        - 다른 트랜잭션은 정상적으로 INSERT/UPDATE 가능

    4. COMMIT (읽기 전용이라 변경 없음)

    **핵심: InnoDB의 MVCC 덕분에 "락 없이 일관된 읽기" 가능**

**MVCC가 뭐냐고?** 04장(트랜잭션)과 05장(격리수준)에서 배운 그거다.

!!! note "MVCC와 mysqldump"
    **MVCC (Multi-Version Concurrency Control):** 데이터를 수정할 때 원본을 유지하고 새 버전을 만든다. 읽는 쪽은 자기 트랜잭션 시작 시점의 버전을 본다. 쓰는 쪽은 새 버전에 쓴다. 서로 안 겹침 → 락 불필요.

    **mysqldump가 이걸 이용:** "내가 시작한 시점의 데이터만 보여줘" → 그 동안 누가 INSERT하든 UPDATE하든 상관없음 → 내 스냅샷에는 안 보이니까.

**제한 사항:**

!!! warning "--single-transaction 제한 사항"
    1. **InnoDB에서만 동작** -- MyISAM 테이블이 섞여 있으면 그 테이블은 일관성 보장 안 됨
    2. **장시간 백업 시 Undo 로그 증가** -- 스냅샷 유지하려면 그 동안의 변경을 Undo에 보관해야 함. 43GB 테이블 덤프에 20분 걸리면 20분간의 Undo 로그가 쌓임
    3. **DDL과 충돌** -- 백업 중에 ALTER TABLE 하면? Metadata Lock 발생 → 06장에서 배운 그거

### 3.4 mysqldump 출력 형태

실제로 어떤 파일이 만들어지는지 모르면 복원할 때 멘붕 온다.

```sql
-- mysqldump 출력 예시 (실제 파일 내용)

-- MySQL dump 10.19  Distrib 10.5.22-MariaDB
-- Server version   10.5.22-MariaDB

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Table structure for table `tb_user`
--

DROP TABLE IF EXISTS `tb_user`;
CREATE TABLE `tb_user` (
  `USER_NO` varchar(20) NOT NULL,
  `USER_NM` varchar(50) DEFAULT NULL,
  `EMAIL` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`USER_NO`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `tb_user`
--

INSERT INTO `tb_user` VALUES
  ('U001','김철수','kim@example.com'),
  ('U002','이영희','lee@example.com'),
  ('U003','박민수','park@example.com');

-- ... (수만 ~ 수억 행)

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
```

**주목할 점:**

!!! warning "주목할 점"
    1. **DROP TABLE IF EXISTS가 먼저 나옴** -- 복원 시 기존 테이블을 지우고 새로 만듦. 실수로 운영 DB에 복원하면? 기존 데이터 날아감!
    2. **INSERT가 멀티 로우로 묶임** -- `VALUES (...), (...), (...);` 한 줄씩 INSERT하는 것보다 훨씬 빠름
    3. **`/*!40101 ... */` 형태** -- MySQL 조건부 실행 (해당 버전 이상에서만 실행). 호환성을 위한 장치
    4. **텍스트 파일이라서** -- grep으로 특정 데이터 검색 가능, sed로 특정 부분만 수정 가능. 이게 논리 백업의 강점

---

## 4. 백업 스크립트 작성

### 4.1 우리 서버 스크립트 분석

실제 `/root/db_backup.sh` 의 구조를 분석한다.

```bash
#!/bin/bash

# ─── 변수 설정 ───
BACKUP_DIR="/backup/mysql"
DB_USER="root"
DB_PASS="P@ss*w0rd!"           # ← 문제 1: 따옴표 없음!
DB_NAME="lxpknu10"
DATE=$(date +%Y%m%d)
KEEP_DAYS=3

# ─── 백업 실행 ───
mysqldump -u $DB_USER -p$DB_PASS $DB_NAME \
  --single-transaction \
  > $BACKUP_DIR/${DB_NAME}_${DATE}.sql

# ─── 압축 ───
tar czf $BACKUP_DIR/${DB_NAME}_${DATE}.tar.gz \
  -C $BACKUP_DIR ${DB_NAME}_${DATE}.sql

# ─── 원본 SQL 삭제 ───
rm -f $BACKUP_DIR/${DB_NAME}_${DATE}.sql

# ─── 오래된 백업 삭제 ───
find $BACKUP_DIR -name "*.tar.gz" -ctime +$KEEP_DAYS -delete
```

**줄별 분석:**

!!! danger "줄별 분석"
    1. `DB_PASS="P@ss*w0rd!"` -- 따옴표 안에 넣었으니 변수 할당은 OK. 하지만 사용할 때가 문제
    2. `mysqldump -u $DB_USER -p$DB_PASS $DB_NAME` -- `-p$DB_PASS`가 셸에서 확장될 때 `-pP@ss*w0rd!` → `*` → glob 패턴으로 확장 (현재 디렉토리 파일 목록!), `!` → bash history 확장 (이전 명령어 참조!). **결과: 비밀번호가 깨짐 → 인증 실패 → 0바이트**
    3. `--single-transaction` -- 이건 제대로 했음
    4. `> $BACKUP_DIR/...` -- 리다이렉션으로 파일 생성. mysqldump가 실패해도 0바이트 파일은 만들어짐! 이래서 0바이트 파일이 5개 있었던 거야
    5. `find ... -ctime +$KEEP_DAYS -delete` -- 3일 넘은 파일 삭제. 0바이트 파일도 삭제됨. 5개만 남아있던 이유: 최근 3일 + 당일 포함

### 4.2 개선된 스크립트

```bash
#!/bin/bash
# ─── 개선된 DB 백업 스크립트 ───

# ─── 변수 설정 ───
BACKUP_DIR="/backup/mysql"
DB_USER="root"
DB_PASS='P@ss*w0rd!'           # ★ 작은따옴표! (셸 확장 방지)
DB_NAME="lxpknu10"
DATE=$(date +%Y%m%d_%H%M%S)    # 시분초 추가 (같은 날 재실행 대비)
KEEP_DAYS=3
LOG_FILE="/var/log/db_backup.log"
IGNORE_TABLE="--ignore-table=${DB_NAME}.tb_lms_exam_stare_paper_backup"

# ─── 디스크 여유 확인 ───
AVAIL_GB=$(df /data --output=avail -B 1G | tail -1 | tr -d ' ')
if [ "$AVAIL_GB" -lt 20 ]; then
    echo "[$(date)] ERROR: 디스크 여유 ${AVAIL_GB}GB < 20GB. 백업 중단." >> $LOG_FILE
    exit 1
fi

# ─── 백업 실행 ───
echo "[$(date)] 백업 시작: $DB_NAME" >> $LOG_FILE

mysqldump -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" \
  --single-transaction \
  --routines \
  --triggers \
  --quick \
  $IGNORE_TABLE \
  2>> $LOG_FILE \
  | gzip > "$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"

# ─── 결과 검증 ───
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${DATE}.sql.gz"
if [ -f "$BACKUP_FILE" ] && [ -s "$BACKUP_FILE" ]; then
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "[$(date)] 백업 성공: $BACKUP_FILE ($SIZE)" >> $LOG_FILE
else
    echo "[$(date)] ERROR: 백업 실패! 파일 없거나 0바이트" >> $LOG_FILE
    rm -f "$BACKUP_FILE"    # 0바이트 파일 정리
    exit 1
fi

# ─── 오래된 백업 삭제 ───
DELETED=$(find "$BACKUP_DIR" -name "*.sql.gz" -ctime +$KEEP_DAYS -delete -print | wc -l)
echo "[$(date)] 오래된 백업 ${DELETED}개 삭제" >> $LOG_FILE

echo "[$(date)] 백업 완료" >> $LOG_FILE
```

**개선 포인트:**

| # | 기존 | 개선 |
|---|------|------|
| 1 | 비밀번호 따옴표 없음 | 작은따옴표 + 큰따옴표로 감쌈 |
| 2 | --ignore-table 없음 | 43GB 테이블 제외 |
| 3 | 에러 로깅 없음 | /var/log/db_backup.log 기록 |
| 4 | 결과 검증 없음 | 파일 존재 + 크기 검증 |
| 5 | --routines 없음 | 스토어드 프로시저 포함 |
| 6 | --triggers 암묵적 | 명시적으로 포함 |
| 7 | 디스크 여유 확인 없음 | 20GB 미만이면 중단 |
| 8 | sql → tar.gz 2단계 | 파이프로 직접 gzip (중간파일X) |
| 9 | 날짜만 | 날짜+시분초 (재실행 대비) |

### 4.3 셸에서 비밀번호 특수문자 문제

이걸 대충 넘기면 14개월 동안 백업이 죽는다. 우리가 그 증거.

!!! danger "셸에서 특수문자가 뭘 하는지 알아야 한다"
    **비밀번호:** `P@ss*w0rd!`

    | 문자 | 셸에서의 의미 |
    |------|---------------|
    | `*` | glob 패턴 (현재 디렉토리 파일 목록으로 확장됨) |
    | `!` | bash history 확장 (이전 명령어 참조) |
    | `$` | 변수 확장 ($HOME → /root) |
    | `` ` `` | 명령어 치환 |
    | `\` | 이스케이프 |
    | `"` | 큰따옴표 (변수 확장 O, glob X) |
    | `'` | 작은따옴표 (모든 확장 차단) |
    | `(` | 서브셸 시작 |
    | `;` | 명령어 구분 |
    | `\|` | 파이프 |
    | `&` | 백그라운드 실행 |
    | `>` | 리다이렉션 |
    | `~` | 홈 디렉토리 확장 |
    | `#` | 주석 시작 |
    | `@` | 배열 확장 (`${arr[@]}`) |

**따옴표 차이를 정확히 이해해야 한다:**

```bash
PASS='P@ss*w0rd!'

# ─── Case 1: 따옴표 없음 (위험!) ───
echo $PASS
# → * 가 현재 디렉토리 파일목록으로 확장됨
# → ! 가 history 확장됨
# → 결과: 비밀번호가 완전히 다른 문자열이 됨

# ─── Case 2: 큰따옴표 (부분 보호) ───
echo "$PASS"
# → 변수 확장은 됨 ($PASS의 값이 들어감)
# → 그런데 이미 변수 할당 시 작은따옴표로 보호했으면 OK
# → 변수에 들어간 후에는 glob/history 확장 안 됨

# ─── Case 3: 작은따옴표 (완전 보호) ───
echo '$PASS'
# → 출력: $PASS (문자 그대로)
# → 변수 확장도 안 됨!

# ─── 결론: 비밀번호 할당은 작은따옴표 ───
DB_PASS='P@ss*w0rd!'        # 할당: 작은따옴표 (확장 완전 차단)

# ─── 사용할 때는 큰따옴표 ───
mysqldump -u root -p"$DB_PASS" lxpknu10
# → -p"P@ss*w0rd!" → 비밀번호 그대로 전달
```

**왜 이게 14개월 동안 방치됐나?**

!!! warning "왜 14개월 동안 방치됐나?"
    1. **스크립트 작성할 때 테스트 안 함** -- "돌리면 되겠지" → 안 됨
    2. **에러 로그를 안 봄** -- 0바이트 파일이 생성돼도 알 수 없음. 에러가 /dev/null로 갔거나 아예 기록 안 됨
    3. **결과 검증 없음** -- 파일 크기가 0인지 확인하는 로직 없음
    4. **알림 없음** -- 실패해도 이메일/슬랙 알림 없음

    **교훈: 자동화의 핵심은 "실행"이 아니라 "검증 + 알림"**

---

## 5. crontab

### 5.1 crontab이란

!!! note "crontab이란?"
    **크론(cron)** = 유닉스/리눅스의 작업 스케줄러. **크론탭(crontab)** = 크론에 등록할 작업 목록 (cron table).

    **비유:** 알람 앱. 매일 오전 7시에 알람 울리게 설정 = crontab 등록. 알람이 울리면 일어나기 = 스크립트 실행.

### 5.2 형식

!!! tip "crontab 형식"
    ```
    분(0-59) 시(0-23) 일(1-31) 월(1-12) 요일(0-7) 실행할 명령어
    ```

    `* * * * *` -- 각 위치는 분, 시, 일, 월, 요일 순서 (0과 7은 일요일)

### 5.3 예시

```bash
# 매일 00:00에 백업
0 0 * * * /root/db_backup.sh

# 매시 30분에 실행
30 * * * * /root/check_disk.sh

# 평일 9시~18시 매시 정각에 실행
0 9-18 * * 1-5 /root/monitor.sh

# 매월 1일 03:00에 실행
0 3 1 * * /root/monthly_report.sh

# 5분마다 실행
*/5 * * * * /root/health_check.sh

# 매주 일요일 02:00에 실행
0 2 * * 0 /root/weekly_cleanup.sh
```

**우리 서버 설정:**

```bash
# crontab -l 결과
0 0 * * * /root/db_backup.sh
# → 매일 00:00에 db_backup.sh 실행
# → 14개월 동안 매일 실행됨
# → 14개월 동안 매일 실패함
# → 아무도 몰랐음
```

### 5.4 crontab 관리 명령어

```bash
# 현재 등록된 작업 확인
crontab -l

# 편집 (vi 에디터로 열림)
crontab -e

# 특정 사용자의 crontab 확인 (root만 가능)
crontab -l -u mysql

# 주의: crontab -r = 전체 삭제! (오타 위험)
# -e와 -r이 키보드에서 옆에 있음
# crontab -e 치려다 crontab -r 치면? → 전체 작업 삭제
```

### 5.5 cron 에러 로그 확인

```bash
# cron 실행 로그
cat /var/log/cron

# 시스템 로그에서 cron 관련 확인
grep CRON /var/log/syslog

# cron 작업의 출력을 로그로 남기기
0 0 * * * /root/db_backup.sh >> /var/log/db_backup_cron.log 2>&1

# 2>&1 의미:
#   2 = 표준 에러 (stderr)
#   > = 리다이렉션
#   &1 = 표준 출력 (stdout)과 같은 곳으로
#   → 에러도 같은 로그 파일에 기록
```

---

## 6. 백업 검증

백업했다고 끝이 아니다. **검증 안 한 백업은 백업이 아니다.**

### 6.1 파일 크기 확인

```bash
# 백업 파일 크기 확인
ls -lh /backup/mysql/

# 정상 예시:
# -rw-r--r-- 1 root root 2.1G Mar 06 00:15 lxpknu10_20260306.sql.gz

# 비정상 예시 (우리 서버 14개월간의 상태):
# -rw-r--r-- 1 root root    0 Mar 06 00:00 lxpknu10_20260306.sql.gz
# -rw-r--r-- 1 root root    0 Mar 05 00:00 lxpknu10_20260305.sql.gz
# -rw-r--r-- 1 root root    0 Mar 04 00:00 lxpknu10_20260304.sql.gz
# → 전부 0바이트 → 전부 실패
```

**자동 검증 (스크립트에 넣어야 할 것):**

```bash
# -s 옵션: 파일이 존재하고 크기가 0보다 큰지
if [ -s "$BACKUP_FILE" ]; then
    echo "백업 성공"
else
    echo "백업 실패! 0바이트 또는 파일 없음"
    # 알림 발송 (메일, 슬랙 등)
fi

# 최소 크기 검증 (너무 작으면 의심)
SIZE=$(stat -c%s "$BACKUP_FILE")
MIN_SIZE=$((100 * 1024 * 1024))   # 100MB
if [ "$SIZE" -lt "$MIN_SIZE" ]; then
    echo "경고: 백업 파일이 비정상적으로 작음 (${SIZE} bytes)"
fi
```

### 6.2 압축 파일 무결성

```bash
# gzip 무결성 검사
gzip -t /backup/mysql/lxpknu10_20260306.sql.gz
# → 정상이면 출력 없음
# → 손상이면 에러 메시지

# tar.gz 무결성 검사
tar tzf /backup/mysql/lxpknu10_20260306.tar.gz > /dev/null
# → 정상이면 출력 없음
# → 손상이면 에러 메시지
```

### 6.3 실제 복원 테스트 (가장 확실한 검증)

!!! danger "백업 파일이 있다 ≠ 복원할 수 있다"
    정기적으로 테스트 서버에 복원해봐야 한다.

    1. 테스트 서버 준비 (절대 운영 서버에서 하지 마)
    2. 백업 파일 복원
    3. 데이터 건수 확인
    4. 주요 쿼리 실행해서 결과 확인

    **최소 월 1회 복원 테스트 권장.**

```bash
# 복원 명령
# ★ 주의: 운영 서버에서 절대 실행하지 마!

# sql.gz 파일 복원
gunzip < /backup/mysql/lxpknu10_20260306.sql.gz | mysql -u root -p'pass' lxpknu10_test

# sql 파일 복원
mysql -u root -p'pass' lxpknu10_test < /backup/mysql/lxpknu10_20260306.sql

# 복원 후 검증
mysql -u root -p'pass' -e "SELECT COUNT(*) FROM lxpknu10_test.tb_user;"
```

---

## 7. RPO와 RTO

### 7.1 RPO (Recovery Point Objective)

!!! note "RPO = 최대 얼마만큼의 데이터 손실을 허용할 수 있는가?"
    **비유:** 게임 세이브 포인트. 마지막 세이브가 1시간 전이면, 장애 시 최대 1시간의 플레이를 잃는다. RPO = 1시간.

    | 상황 | RPO |
    |------|-----|
    | 우리 서버 (매일 00:00 백업) | 24시간 (최악의 경우 하루치 데이터 손실) |
    | 14개월간 백업 실패 | **무한대 (복구 불가)** |

    23:59에 장애 나면 00:00 이후 모든 데이터 날아감. 14개월 동안 "최대 데이터 손실 = 전부"인 상태로 운영됨. 이게 얼마나 위험한 건지 이해돼?

### 7.2 RTO (Recovery Time Objective)

!!! note "RTO = 장애 발생 후 서비스 복구까지 최대 허용 시간"
    **비유:** 정전 후 복구. 병원: RTO = 0초 (UPS 있음). 카페: RTO = 몇 시간 (좀 기다려도 됨).

    | 백업 방식 | 복원 시간 | RTO |
    |----------|----------|-----|
    | mysqldump 7GB SQL 복원 | 30분~1시간 | 최소 1시간 |
    | mysqldump 43GB SQL 복원 | 수 시간 | 수 시간 |
    | 물리 백업 (xtrabackup) | 파일 복사 + crash recovery | 10~20분 |

### 7.3 백업 전략과의 관계

| 전략 | RPO | RTO |
|------|-----|-----|
| 백업 없음 | ∞ | ∞ |
| 일 1회 mysqldump | 24시간 | 1~수시간 |
| 일 1회 mysqldump + binlog | 수 분 | 1~수시간 |
| 일 1회 xtrabackup | 24시간 | 10~30분 |
| 일 1회 xtrabackup + binlog | 수 분 | 10~30분 |
| 실시간 복제 (Master-Slave) | 수 초 | 수 분 |
| Galera Cluster (Multi-Master) | 0 | 0 |

!!! tip "binlog란?"
    DB의 모든 변경 사항을 기록하는 로그.
    백업 시점 + binlog = 백업 이후 변경까지 복구 가능.
    12장에서 자세히 다룬다.

---

## 8. 보관 정책

### 8.1 find -ctime 동작 원리

```bash
find /backup -name "*.tar.gz" -ctime +3 -delete
```

이 명령어가 정확히 뭘 하는지 안다고?

!!! note "-ctime +3 의 의미"
    `ctime` = 파일 상태 변경 시간 (Change Time). `+3` = 3일 초과 (72시간 이상 지난 파일). **주의:** +3은 "3일 이상"이 아니라 "3일 초과"!

    | 파일 생성일 (오늘 3월 6일) | 경과일 | +3 조건 | 결과 |
    |--------------------------|--------|---------|------|
    | 3월 6일 (오늘) | 0일 | 0 > 3? X | 유지 |
    | 3월 5일 | 1일 | 1 > 3? X | 유지 |
    | 3월 4일 | 2일 | 2 > 3? X | 유지 |
    | 3월 3일 | 3일 | 3 > 3? X | **유지** (3일은 "초과"가 아님) |
    | 3월 2일 | 4일 | 4 > 3? O | 삭제 |

    0바이트 파일 5개가 남아있던 이유: 당일(1) + 최근 3일(3) + 경계(1) = 최대 5개

**비슷한 옵션들:**

!!! tip "비슷한 옵션들"
    | 옵션 | 기준 |
    |------|------|
    | `-ctime` | 파일 상태 변경 시간 (Change Time) |
    | `-mtime` | 파일 내용 수정 시간 (Modify Time) |
    | `-atime` | 파일 접근 시간 (Access Time) |

    | 표기 | 의미 | 예시 |
    |------|------|------|
    | `+N` | N일 초과 | `find . -mtime +7` → 7일 초과 (8일 이상 전) |
    | `-N` | N일 미만 | `find . -mtime -1` → 1일 미만 (24시간 이내) |
    | `N` | 정확히 N일 | `find . -mtime 3` → 정확히 3일 전 (72~96시간) |

### 8.2 보관 기간 결정

!!! abstract "보관 기간 결정"
    보관 기간 = f(백업 파일 크기, 가용 디스크, 복구 요구사항)

    **우리 서버 계산:** 디스크 전체 196GB, DB 데이터 54GB (TRUNCATE 후), 여유 ~120GB. 백업 파일 크기 (gzip 압축 후) 정상 DB (~7GB) → 덤프 ~10GB → gzip ~2GB. 보관 가능: 120GB / 2GB = 60일 (이론적).

    | 보관일수 | 장점 | 단점 |
    |----------|------|------|
    | 3일 | 디스크 절약 | 복구 기간 짧음 |
    | 7일 | 적당한 균형 | 14GB 사용 |
    | 14일 | 넉넉한 복구 기간 | 28GB 사용 |
    | 30일 | 월간 추이 확인 가능 | 60GB 사용 |

    권장: 최소 7일, 권장 14일, 여유 있으면 30일. 기존 3일은 너무 짧다. 금요일에 잘못된 데이터 넣고 월요일에 발견하면? → 3일 지나서 백업 삭제됨 → 복구 불가.

---

## 9. 실전 사례 종합: 14개월간의 백업 실패

!!! example "타임라인 복원"
    **2024-06-21** Disk full 에러 최초 발생

    - 디스크 134GB (72%) 사용
    - mysqldump 출력 예상 73GB > 여유 53GB
    - 덤프 도중 Disk Full → 0바이트 파일 생성

    **2024-06 ~ 2026-02** 매일 00:00 백업 시도 → 매일 실패

    - 0바이트 파일 생성 → find -ctime +3 → 삭제 → 반복
    - 229건의 Disk full 에러 축적
    - 아무도 확인 안 함

    **근본 원인 추적:**

    ```mermaid
    flowchart TD
        A["코드 버그"] --> B["jQuery 이벤트 핸들러 중복 등록"]
        B --> C["시험 저장 AJAX N배 증폭"]
        C --> D["테이블 2.7억 건 축적"]
        D --> E["테이블 용량 43GB (전체 DB의 86%)"]
        E --> F["mysqldump 출력 73GB 예상"]
        F --> G["디스크 여유 53GB < 73GB"]
        G --> H["Disk Full → mysqldump 실패 → 0바이트 파일"]
        H --> I["14개월간 유효한 백업 없음"]
        I --> J["RPO = ∞ (복구 불가 상태로 운영)"]
    ```

    **해결:**

    1. 코드 버그 수정 (원인 제거)
    2. TRUNCATE TABLE (43GB 확보)
    3. 디스크: 134GB → 54GB (72% → 29%)
    4. --ignore-table 옵션 추가 (재발 방지)
    5. 백업 스크립트 개선 (검증 + 로깅)
    6. 예상 백업 파일 크기: ~2GB (gzip 압축 후)

    **비밀번호 문제 (추가 원인):**

    1. DB_PASS에 특수문자 *! 포함
    2. 셸 스크립트에서 따옴표 미사용
    3. `*` → glob 확장, `!` → history 확장
    4. 비밀번호 깨짐 → 인증 실패 → 0바이트

**왜 2가지 원인이 겹쳤나?**

!!! danger "왜 2가지 원인이 겹쳤나?"
    | 원인 | 영향 |
    |------|------|
    | 원인 1: 비밀번호 특수문자 (따옴표 미사용) | mysqldump 인증 자체가 실패 → 덤프 시작도 못 함 → 0바이트 |
    | 원인 2: 디스크 용량 부족 (43GB 테이블) | 인증이 됐더라도 덤프 중 Disk Full → 불완전 파일 or 0바이트 |

    두 원인 중 하나만 있어도 백업 실패. 둘 다 있었으니 100% 실패. 둘 다 14개월간 방치.

---

## 10. 핵심 정리

!!! abstract "11장 핵심 정리"
    1. **백업 없으면 서비스가 끝난다** -- 하드웨어, 인간 실수, 공격, 버그 -- 언제든 터짐
    2. **논리 백업(mysqldump) vs 물리 백업(xtrabackup)** -- 규모, 이식성, 복원 시간으로 선택
    3. **--single-transaction = InnoDB 백업의 핵심** -- MVCC로 락 없이 일관된 스냅샷
    4. **--ignore-table = 생명줄** -- 불필요한 거대 테이블 하나가 백업 전체를 죽인다
    5. **셸 특수문자는 반드시 작은따옴표로 감쌀 것** -- `*` `!` `$` `` ` `` 전부 셸이 먹는다
    6. **백업 = 실행 + 검증 + 알림** -- 실행만 하면 14개월간 0바이트 모른다
    7. **RPO/RTO를 알아야 백업 전략을 세운다** -- "매일 백업"이 충분한지 아닌지는 허용 데이터 손실 시간으로 판단
    8. **보관 기간: 디스크 vs 복구 필요 기간의 트레이드오프** -- 3일은 너무 짧다. 최소 7일.
    9. **정기적으로 복원 테스트할 것** -- "파일이 있다" ≠ "복원된다"

---

**다음 장에서 배울 것:**

12장 "디스크와 DB의 관계"에서는 디스크 레벨에서 DB를 본다.
df -h가 뭘 보여주는지, Disk Full이 DB에 어떤 연쇄 장애를 일으키는지,
134GB에서 54GB로 줄이기까지 뭘 했는지.

**"백업이 왜 실패했는지"는 이 장에서 배웠다.**
**"그 실패 조건(디스크)을 어떻게 관리하는지"는 다음 장이다.**
