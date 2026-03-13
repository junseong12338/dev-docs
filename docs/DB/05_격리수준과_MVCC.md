# 05. 격리 수준과 MVCC

---

## 1. 동시성 문제가 왜 발생하는가

### 1.1 근본적인 질문

DB는 혼자 쓰는 거 아니야. 수십, 수백 개의 커넥션이 **동시에** 같은 테이블, 같은 행에 접근한다.

!!! question "동시성 문제의 핵심"
    - 트랜잭션 A: `UPDATE tb_student SET score = 95 WHERE id = 1;`
    - 트랜잭션 B: `SELECT score FROM tb_student WHERE id = 1;`

    둘이 동시에 실행되면?
    B가 읽는 score는 95야? 원래 값이야?
    A가 아직 COMMIT 안 했으면?

### 1.2 비유: 같은 문서를 두 사람이 동시에 편집

!!! example "비유: Google Docs 동시 편집"
    A: 3번째 줄을 "점수: 80" → "점수: 95"로 수정 중 (아직 저장 안 함)
    B: 같은 문서를 열어서 3번째 줄을 읽음

    B가 보는 건 뭐야?

    - 80? (A가 수정하기 전 원본)
    - 95? (A가 수정 중인 값)

    이게 동시성 문제의 본질이다.
    DB에서는 이걸 "격리 수준"으로 제어한다.

### 1.3 왜 그냥 한 명씩 하면 안 되나?

!!! warning "왜 그냥 한 명씩 하면 안 되나?"
    "한 명이 끝날 때까지 다른 사람 기다려!" → SERIALIZABLE

    가능은 하지. 근데:

    - 100명이 동시 접속하면 1명만 작업, 99명은 대기
    - 응답 시간 100배 증가
    - 사실상 서비스 불능

    그래서 "적당히 격리하면서 적당히 동시에" 하는 게 필요하다.
    이게 격리 수준(Isolation Level)이야.

---

## 2. 동시성 문제 3가지

동시성 문제는 정확히 3가지가 있다. 이걸 모르면 격리 수준을 이해할 수 없다.

### 2.1 Dirty Read (더티 리드)

**한 줄 정의: 커밋 안 된 데이터를 읽는 것.**

!!! danger "Dirty Read 시나리오"
    | 시간 | 트랜잭션 A | 트랜잭션 B |
    |------|-----------|-----------|
    | T1 | BEGIN; | |
    | T2 | UPDATE tb_student SET score = 95 WHERE id = 1; (원래 score = 80) | |
    | T3 | | BEGIN; |
    | T4 | | SELECT score FROM tb_student WHERE id = 1; → **결과: 95** !! |
    | T5 | ROLLBACK; (score가 80으로 복원) | (B는 95를 믿고 로직 처리) |

    **결과:** B가 읽은 95는 존재한 적 없는 값 → **Dirty Read**

**왜 위험한가:**

!!! warning "왜 위험한가"
    B가 읽은 95는 "존재한 적 없는 유령 데이터"다.
    A가 ROLLBACK했으니 score는 계속 80이었던 거야.
    근데 B는 95로 처리해버렸어.

    **실전 예시:**

    - B가 95점을 기준으로 "합격 처리"를 했다면?
    - 실제로는 80점인데 합격?
    - 데이터 무결성 완전히 깨짐

**발생 조건:** 격리 수준이 READ UNCOMMITTED일 때만 발생.

---

### 2.2 Non-Repeatable Read (반복 불가능한 읽기)

**한 줄 정의: 같은 쿼리를 두 번 날렸는데 결과가 다른 것.**

!!! warning "Non-Repeatable Read 시나리오"
    | 시간 | 트랜잭션 A | 트랜잭션 B |
    |------|-----------|-----------|
    | T1 | BEGIN; | |
    | T2 | SELECT score FROM tb_student WHERE id = 1; → **결과: 80** | |
    | T3 | | BEGIN; |
    | T4 | | UPDATE tb_student SET score = 95 WHERE id = 1; |
    | T5 | | COMMIT; |
    | T6 | SELECT score FROM tb_student WHERE id = 1; → **결과: 95** !! | |

    **결과:** A의 같은 SELECT인데 T2에서 80, T6에서 95 → **Non-Repeatable Read**

**Dirty Read와의 차이:**

!!! note "Dirty Read와의 차이"
    | 문제 | 특징 |
    |------|------|
    | Dirty Read | 커밋 안 된 값을 읽음 (유령 데이터) |
    | Non-Repeatable | 커밋 된 값을 읽음 (실제 데이터) |

    Non-Repeatable Read는 B가 정상적으로 COMMIT한 데이터를 읽은 거야.
    "틀린 값"은 아니지만, A 입장에서 "같은 쿼리 결과가 달라지는" 게 문제.

    **왜 문제냐:**

    - A가 T2에서 score=80 읽고, 이걸 기반으로 로직을 처리하는 중
    - T6에서 다시 읽었더니 95로 바뀌어 있음
    - A의 로직이 일관성 없는 데이터로 동작

**발생 조건:** READ UNCOMMITTED, READ COMMITTED에서 발생.

---

### 2.3 Phantom Read (팬텀 리드)

**한 줄 정의: 없던 행이 갑자기 나타나는 것.**

!!! warning "Phantom Read 시나리오"
    | 시간 | 트랜잭션 A | 트랜잭션 B |
    |------|-----------|-----------|
    | T1 | BEGIN; | |
    | T2 | SELECT COUNT(*) FROM tb_student WHERE class = '1반'; → **결과: 30명** | |
    | T3 | | BEGIN; |
    | T4 | | INSERT INTO tb_student (name, class) VALUES ('신입생', '1반'); |
    | T5 | | COMMIT; |
    | T6 | SELECT COUNT(*) FROM tb_student WHERE class = '1반'; → **결과: 31명** !! | |

    **결과:** 유령(Phantom)처럼 없던 행이 나타남 → **Phantom Read**

**Non-Repeatable Read와의 차이:**

!!! note "Non-Repeatable Read와의 차이"
    | 문제 | 원인 | 대상 |
    |------|------|------|
    | Non-Repeatable | UPDATE | 기존 행의 값이 바뀜 |
    | Phantom | INSERT/DELETE | 새로운 행이 나타남/사라짐 |

    **핵심 차이:**
    Non-Repeatable은 "같은 행"의 값이 바뀐 거.
    Phantom은 "행의 수 자체"가 바뀐 거.

    **왜 따로 구분하냐:**

    - 기존 행에 락을 걸면 Non-Repeatable은 방지할 수 있어
    - 근데 아직 존재하지 않는 행에는 락을 걸 수 없잖아
    - 그래서 Phantom은 별도 메커니즘(Gap Lock)이 필요

---

## 3. 격리 수준 4단계

### 3.1 전체 정리 표

| 격리 수준 | Dirty Read | Non-Repeatable Read | Phantom Read |
|-----------|-----------|-------------------|-------------|
| **READ UNCOMMITTED** | 발생 | 발생 | 발생 |
| **READ COMMITTED** | 방지 | 발생 | 발생 |
| **REPEATABLE READ** | 방지 | 방지 | 발생* |
| **SERIALIZABLE** | 방지 | 방지 | 방지 |

!!! note "InnoDB의 REPEATABLE READ"
    InnoDB/MariaDB의 REPEATABLE READ는 MVCC + Gap Lock으로 Phantom Read도 대부분 방지한다. 표준 SQL 스펙상은 "발생"이지만 실제 InnoDB에서는 거의 발생하지 않는다.

### 3.2 각 수준별 상세

#### READ UNCOMMITTED — "문 안 잠그고 편집"

!!! danger "READ UNCOMMITTED"
    - 다른 트랜잭션의 커밋 안 된 변경도 읽음
    - 가장 빠르지만 가장 위험
    - 실무에서 거의 안 씀

    **언제 쓰냐:** 정확도보다 속도가 중요할 때, 대략적인 통계만 필요할 때 (쓰지 마. 진짜로.)

#### READ COMMITTED — "저장된 버전만 읽기"

!!! note "READ COMMITTED"
    - COMMIT된 데이터만 읽음
    - Dirty Read 방지
    - 하지만 같은 쿼리가 다른 결과 나올 수 있음 (Non-Repeatable)
    - Oracle 기본 격리 수준

    **우리 서버에서:**
    INNODB_TRX에서 READ COMMITTED 트랜잭션이 보였던 이유는
    mysqldump가 --single-transaction 옵션으로 실행되면서
    특정 작업에서 READ COMMITTED를 사용했기 때문

#### REPEATABLE READ — "내가 시작한 시점의 스냅샷"

!!! tip "REPEATABLE READ (MariaDB 기본)"
    - 트랜잭션 시작 시점의 데이터를 계속 읽음
    - 다른 트랜잭션이 COMMIT해도 영향 없음
    - **MariaDB/MySQL InnoDB의 기본 격리 수준**

    **동작 원리:**

    - 트랜잭션 시작 시 "스냅샷"을 찍음
    - 이후 모든 SELECT는 이 스냅샷을 기준으로 읽음
    - 다른 트랜잭션이 100번 COMMIT해도 내 스냅샷은 안 바뀜
    - 이게 MVCC의 핵심이다

#### SERIALIZABLE — "한 줄로 서시오"

!!! warning "SERIALIZABLE"
    - 모든 SELECT가 자동으로 공유 락을 걺
    - 사실상 트랜잭션이 직렬 실행되는 효과
    - 동시성 문제 0%, 성능도 0%

    **왜 안 쓰냐:**

    - 100명 동시 접속 → 1명씩 순서대로 처리
    - 응답 시간 폭증, 데드락 가능성 증가
    - 특수한 금융 거래 같은 곳에서만 제한적으로 사용

### 3.3 트레이드오프

!!! tip "트레이드오프"
    **격리 수준 높임 (SERIALIZABLE 방향):**

    - 데이터 안정성 향상
    - 동시 처리량 감소
    - 락 대기 시간 증가
    - 데드락 가능성 증가

    **격리 수준 낮춤 (READ UNCOMMITTED 방향):**

    - 데이터 안정성 감소
    - 동시 처리량 증가
    - 락 대기 시간 감소
    - 데드락 가능성 감소

    **MariaDB 기본값: REPEATABLE READ** → 대부분의 웹 서비스에 적합한 "중간 지점". MVCC 덕분에 읽기 성능이 좋으면서 일관성도 보장.

### 3.4 현재 격리 수준 확인

```sql
-- 세션 격리 수준 확인
SELECT @@tx_isolation;
-- 또는 (MariaDB 10.5+)
SELECT @@transaction_isolation;

-- 글로벌 격리 수준 확인
SELECT @@global.tx_isolation;
```

---

## 4. MVCC (Multi-Version Concurrency Control)

### 4.1 MVCC란?

**한 줄 정의: 같은 데이터의 여러 버전을 동시에 유지하는 기법.**

!!! note "MVCC의 핵심 원리"
    **MVCC 이전 (락 기반 동시성 제어):**

    - A가 쓰는 동안 B는 읽지도 못함 (대기) → 성능 저하

    **MVCC 이후:**

    - A가 쓰는 동안 B는 "이전 버전"을 읽음
    - A의 쓰기와 B의 읽기가 동시에 진행
    - 서로 차단하지 않음 → 성능 향상

    **핵심:** "읽기는 쓰기를 차단하지 않고, 쓰기는 읽기를 차단하지 않는다."

비유로 설명하면:

!!! example "도서관의 책 비유"
    **락 기반:**
    A가 책을 빌리면 B는 A가 반납할 때까지 대기
    → 한 번에 한 명만 읽을 수 있음

    **MVCC:**
    A가 책을 가져가면 도서관이 즉시 복사본을 만들어둠
    B가 오면 복사본을 읽음
    A가 반납하면 원본 업데이트

    **차이:**

    | 방식 | 원본 | 접근 |
    |------|------|------|
    | 락 기반 | 원본 1개 | 순서대로 접근 |
    | MVCC | 여러 버전 동시 존재 | 동시 접근 가능 |

### 4.2 MVCC 동작 원리

#### Undo 로그를 이용한 버전 관리

!!! tip "Undo 로그의 진짜 역할"
    04장에서 배운 Undo 로그 기억나?
    "ROLLBACK을 위한 로그"라고만 배웠다.
    근데 Undo 로그의 진짜 역할은 MVCC에 있다.

!!! example "Undo 로그 버전 체인"
    - **현재 데이터:** id=1, score=95, trx_id=200
    - ↓
    - **Undo 로그:** id=1, score=80, trx_id=100
    - ↓
    - **Undo 로그:** id=1, score=70, trx_id=50

    같은 행의 3가지 버전이 존재하며, 각 트랜잭션은 자기 시작 시점에 맞는 버전을 읽음

#### 트랜잭션 ID와 스냅샷

!!! note "MVCC 동작 순서"
    1. 트랜잭션 시작 시 고유 ID 부여 (예: trx_id = 150)
    2. 시작 시점에 "활성 트랜잭션 목록" 스냅샷 생성 → "지금 아직 COMMIT 안 한 트랜잭션들: [120, 135, 148]"
    3. SELECT 실행 시 가시성(Visibility) 판단:
        - 행의 trx_id < 150이고 활성 목록에 없으면 → **보임**
        - 행의 trx_id가 활성 목록에 있으면 → **안 보임** (Undo에서 읽음)
        - 행의 trx_id >= 150이면 → **안 보임** (내 이후에 생긴 거)
    4. 안 보이는 행은 Undo 로그 체인을 따라가서 자기가 볼 수 있는 버전을 찾음

#### Consistent Read (일관된 읽기)

!!! example "Consistent Read (일관된 읽기) - REPEATABLE READ 동작"
    | 시간 | 동작 | 설명 |
    |------|------|------|
    | T1 | 트랜잭션 A 시작 (trx_id = 100) | 이 시점의 스냅샷 생성 |
    | T2 | 트랜잭션 B가 score 80→95 UPDATE 후 COMMIT (trx_id = 200) | |
    | T3 | 트랜잭션 A가 SELECT | 현재 행: score=95, trx_id=200. 200 > 100 → "내 이후에 바뀐 거니까 안 보여" → Undo에서 score=80 찾음. **결과: 80** |
    | T4 | 트랜잭션 A가 다시 SELECT | 같은 과정 반복. **결과: 80** (일관됨!) |

    이게 Consistent Read야.
    트랜잭션이 살아있는 동안 "스냅샷 시점의 데이터"를 계속 읽는 거다.
    REPEATABLE READ가 "반복 가능한 읽기"인 이유가 바로 이것.

### 4.3 격리 수준별 MVCC 동작 차이

!!! tip "READ COMMITTED vs REPEATABLE READ"
    **READ COMMITTED:**

    - SELECT할 때마다 새로운 스냅샷 생성
    - 다른 트랜잭션이 COMMIT하면 다음 SELECT에 반영됨
    - "최신 커밋된 데이터"를 읽음

    **REPEATABLE READ:**

    - 트랜잭션 시작 시 한 번만 스냅샷 생성
    - 끝까지 그 스냅샷을 사용
    - "시작 시점의 데이터"를 읽음

    **차이:** RC는 매 SELECT마다 새 스냅샷 → Non-Repeatable Read 발생 / RR은 첫 스냅샷 고정 → Non-Repeatable Read 방지

### 4.4 MVCC와 mysqldump --single-transaction

04장에서 우리 서버에서 mysqldump가 돌고 있었지?
이제 그게 왜 서비스에 영향을 안 주는지 이해할 수 있다.

!!! example "mysqldump --single-transaction 동작 원리"
    1. mysqldump가 `START TRANSACTION WITH CONSISTENT SNAPSHOT` 실행 → REPEATABLE READ로 트랜잭션 시작 → 이 시점의 스냅샷 고정
    2. 테이블별 `SELECT * FROM ...` 실행 → 모두 스냅샷 시점의 데이터를 읽음 → 덤프 도중 다른 트랜잭션이 INSERT/UPDATE/DELETE 해도 mysqldump는 스냅샷 시점 데이터만 봄
    3. **결과:** 모든 테이블이 "같은 시점"의 일관된 데이터. 서비스(INSERT/UPDATE)와 동시 실행 가능. 테이블 락 불필요.

    **핵심:** MVCC가 있으니까 락 없이 일관된 백업이 가능한 것. MVCC 없었으면 전체 DB 락 걸고 백업해야 하고 서비스 중단 불가피.

### 4.5 MVCC의 비용

!!! warning "MVCC의 비용"
    공짜는 없다. MVCC도 비용이 있다.

    **1. Undo 로그 크기 증가**

    → 오래된 트랜잭션이 있으면 Undo 로그 정리 불가
    → 디스크 사용량 증가
    → 04장에서 배운 "Undo Purge"가 이걸 정리하는 거야

    **2. Undo 로그 체인 탐색 비용**

    → 버전이 많으면 원하는 버전 찾을 때까지 체인을 타고 감
    → 긴 트랜잭션 = 긴 체인 = 느린 읽기

    **3. 우리 사례에서의 교훈**

    → Sleep 상태로 트랜잭션을 오래 열어두면?
    → 그 트랜잭션 시작 이후의 모든 Undo 로그를 유지해야 함
    → 서버 전체 성능에 영향

    **결론: 트랜잭션은 짧게. 열었으면 빨리 닫아. 긴 트랜잭션 = MVCC의 적.**

---

## 5. 우리 서버에 대입

### 5.1 READ COMMITTED 트랜잭션이 보였던 이유

!!! warning "READ COMMITTED 트랜잭션이 보였던 이유"
    INNODB_TRX에서 이런 게 보였다:

    - trx_isolation_level: READ COMMITTED
    - trx_state: RUNNING
    - trx_started: 2시간 전

    **왜 READ COMMITTED?**

    - mysqldump --single-transaction은 기본적으로 REPEATABLE READ로 시작하지만, 내부적으로 일부 작업은 READ COMMITTED로 수행
    - 또는 애플리케이션에서 격리 수준을 명시적으로 설정한 경우

    **어느 쪽이든 핵심은:**

    - "이 트랜잭션이 2시간째 RUNNING"이라는 사실
    - 2시간 동안 메타데이터 공유 락을 잡고 있었다는 사실
    - 이게 TRUNCATE의 메타데이터 배타 락과 충돌했다는 사실

### 5.2 전체 그림 연결

!!! note "전체 그림 연결"
    **04장에서 배운 것:** 트랜잭션 = BEGIN ~ COMMIT/ROLLBACK. 열려있는 트랜잭션 = 자원 점유 중.

    **05장에서 배운 것 (지금):** 격리 수준 → MVCC → 스냅샷 기반 읽기. 열려있는 트랜잭션 → Undo 로그 유지 + 메타데이터 락 유지.

    **06장에서 배울 것 (다음):** 락의 종류 → 메타데이터 락 상세. TRUNCATE가 왜 "Waiting for table metadata lock"인지. SHOW PROCESSLIST로 범인 찾는 법.

    점점 그림이 맞춰지고 있다.

---

## 6. 핵심 정리

!!! abstract "핵심 정리"
    **동시성 문제 3가지:**

    - Dirty Read: 커밋 안 된 데이터 읽기 (유령)
    - Non-Repeatable: 같은 쿼리, 다른 결과 (UPDATE)
    - Phantom: 없던 행이 나타남 (INSERT)

    **격리 수준 4단계 (아래로 갈수록 안전, 느림):**

    - READ UNCOMMITTED → 전부 발생
    - READ COMMITTED → Dirty Read 방지
    - REPEATABLE READ → + Non-Repeatable 방지 (MariaDB 기본)
    - SERIALIZABLE → 전부 방지, 성능 최악

    **MVCC:** "읽기와 쓰기가 서로 차단하지 않는다". Undo 로그에 이전 버전 유지 → 스냅샷 기반 읽기. REPEATABLE READ는 시작 시점 스냅샷 고정, READ COMMITTED는 SELECT마다 새 스냅샷.

    **mysqldump --single-transaction:** MVCC 덕분에 락 없이 일관된 백업 가능. 스냅샷 시점의 데이터만 읽음.

    **트랜잭션은 짧게:** 긴 트랜잭션 = Undo 로그 증가 + 메타데이터 락 유지 → 서버 전체 성능에 영향.

    **다음 장:** 락의 세계 → "TRUNCATE가 왜 멈췄는지, 이제 락으로 설명한다"
