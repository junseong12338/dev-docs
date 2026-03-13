# 08. NexClass ↔ LMS 실전 분석 - Omega

---

> 👹 "이론 끝. 이제 진짜야. 우리 프로젝트에서 JWT와 AES가 실제로 어떻게 쓰이는지 봐.
> 코드 읽고 전체 흐름을 머릿속에 그릴 수 있어야 해."

---

## 1. 전체 아키텍처

!!! abstract "NexClass ↔ LMS 데이터 동기화 아키텍처"
    **NexClass (Spring Boot 4.x, Java 17)**

    - `LmsSyncService.java` -- 동기화 핵심 서비스
    - `AES256Util.java` -- AES 복호화 유틸
    - `application.properties` -- 키/설정 관리
    - Entity (Term, Course, User, CourseUser)
    - Repository (각 Entity별)

    **요청:** JWT 생성 → HTTP 요청 (Authorization: Bearer {JWT}), Body: {"pageNumber": 0, "pageSize": 1000}

    **LMS (Spring Boot, Java 11)**

    - `VcSyncApiController.java` -- API 엔드포인트
    - `AES256Util.java` -- AES 암호화 (LMS 버전)
    - JWT 검증 로직

    **응답:** JWT 검증 → DB 조회 → AES 암호화 → 응답

    **NexClass가 응답 받아서:**
    AES 복호화 → JSON 파싱 → Entity 변환 → DB 저장

---

## 2. 설정 파일 분석

### application.properties

```properties
# ─── JWT 인증 관련 ───
nexclass.api.key=knu-lms-2026                        # APP_KEY (Payload에 넣을 앱 식별자)
nexclass.api.secret=KnuLmsSecretKey2026!@#0123456789  # SECRET_KEY (서명용 비밀 키)

# ─── AES 복호화 관련 ───
lms.sync.aes-key=MediOpi@85oO!!!!                    # AES 키 (= IV)

# ─── API 호출 관련 ───
lms.sync.base-url=https://www.knu10.cc                # LMS 서버 주소
lms.sync.org-cd=ORG0000001                            # 기관 코드
lms.sync.page-size=1000                                # 페이지당 데이터 수
```

### 각 설정이 어디서 쓰이는지

```
nexclass.api.key     → JWT Payload의 "appKey" 클레임
nexclass.api.secret  → JWT Signature 생성 시 HMAC-SHA256 키
lms.sync.aes-key     → AES256Util 생성자에 전달 → 복호화 키 + IV
lms.sync.base-url    → RestClient 호출 URL의 앞부분
lms.sync.org-cd      → API URL의 쿼리 파라미터 (?orgCd=ORG0000001)
lms.sync.page-size   → 요청 Body의 pageSize 값
```

---

## 3. JWT 생성 코드 분석

### LmsSyncService에서 JWT 만드는 부분

```java
// 설정 파일에서 주입받은 값들
@Value("${nexclass.api.key}")
private String appKey;           // "knu-lms-2026"

@Value("${nexclass.api.secret}")
private String secretKey;        // "KnuLmsSecretKey2026!@#0123456789"

// JWT 토큰 생성 메서드
private String generateToken() {
    return Jwts.builder()
        // ── Payload 구성 ──
        .claim("appKey", appKey)              // ① appKey 클레임 추가
        .issuedAt(new Date())                 // ② iat: 발급 시각 (지금)
        .expiration(new Date(                 // ③ exp: 만료 시각 (30분 뒤)
            System.currentTimeMillis() + 1800000
        ))
        // ── Signature 생성 ──
        .signWith(                            // ④ 서명
            Keys.hmacShaKeyFor(               //    SECRET_KEY → HMAC 키 객체
                secretKey.getBytes(StandardCharsets.UTF_8)
            ),
            Jwts.SIG.HS256                    //    HS256 알고리즘
        )
        .compact();                           // ⑤ Header.Payload.Signature 합치기
}
```

### 이 코드가 만드는 JWT

```
Header:
  {"alg":"HS256","typ":"JWT"}
  → Base64: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9

Payload:
  {"appKey":"knu-lms-2026","iat":1709021100,"exp":1709022900}
  → Base64: eyJhcHBLZXkiOiJrbnUtbG1zLTIwMjYi...

Signature:
  HMAC-SHA256(Header.Payload, "KnuLmsSecretKey2026!@#0123456789")
  → SflKxwRJ...

최종: eyJhbGci...eyJhcHBL...SflKxwRJ...
```

---

## 4. LMS API 호출 코드 분석

### RestClient로 LMS API 호출

```java
@Value("${lms.sync.base-url}")
private String baseUrl;          // "https://www.knu10.cc"

@Value("${lms.sync.org-cd}")
private String orgCd;            // "ORG0000001"

@Value("${lms.sync.page-size}")
private int pageSize;            // 1000

// LMS API 호출 메서드
private String callLmsApi(String type, int pageNumber) {
    String token = generateToken();  // ① 매번 새 JWT 생성

    // ② 요청 Body (페이징 정보)
    Map<String, Object> body = Map.of(
        "pageNumber", pageNumber,    // 0부터 시작
        "pageSize", pageSize         // 1000
    );

    // ③ HTTP POST 요청
    return restClient.post()
        .uri(baseUrl + "/vc/api/sync/" + type + "?orgCd=" + orgCd)
        //    https://www.knu10.cc/vc/api/sync/term?orgCd=ORG0000001
        .header("Authorization", "Bearer " + token)  // ④ JWT 첨부
        .contentType(MediaType.APPLICATION_JSON)
        .body(body)
        .retrieve()
        .body(String.class);  // ⑤ 응답 = 암호화된 문자열
}
```

### 이 코드가 보내는 HTTP 요청

```
POST /vc/api/sync/term?orgCd=ORG0000001 HTTP/1.1
Host: www.knu10.cc
Content-Type: application/json
Authorization: Bearer eyJhbGci...eyJhcHBL...SflKxwRJ...

{"pageNumber": 0, "pageSize": 1000}
```

---

## 5. LMS 응답 처리 (AES 복호화 → JSON 파싱)

### 응답 처리 흐름

```java
@Value("${lms.sync.aes-key}")
private String aesKey;           // "MediOpi@85oO!!!!"

// 응답 처리
private List<Map<String, Object>> processResponse(String encrypted) {
    // ① AES 복호화
    AES256Util aes = new AES256Util(aesKey);
    String json = aes.decrypt(encrypted);

    // ② JSON 파싱
    ObjectMapper mapper = new ObjectMapper();
    Map<String, Object> result = mapper.readValue(json, Map.class);

    // ③ 데이터 추출
    return (List<Map<String, Object>>) result.get("list");
}
```

### 단계별

```mermaid
graph TD
    A["LMS 응답: dKx8mQ2f7hG3nPqR5sT1vW9..."]
    B["AES256Util.decrypt()"]
    C["JSON: resultCode:200, list:[...]<br/>totalCount:2, pageNumber:0, pageSize:1000"]
    D["result.get('list')"]
    E["List&lt;Map&gt;: [{TERM_CD:2026-1, TERM_NAME:1학기},<br/>{TERM_CD:2026-2, TERM_NAME:2학기}]"]

    A --> B --> C --> D --> E
```

---

## 6. Entity 변환 → DB 저장

### Map → Entity → save()

```java
// 학기 동기화 예시
public void syncTerms() {
    String encrypted = callLmsApi("term", 0);          // ① API 호출
    List<Map<String, Object>> list = processResponse(encrypted);  // ② 복호화+파싱

    for (Map<String, Object> item : list) {            // ③ 각 항목 반복
        Term term = Term.builder()
            .termCd((String) item.get("TERM_CD"))      // Map에서 값 꺼내기
            .termName((String) item.get("TERM_NAME"))
            .termYear((String) item.get("TERM_YEAR"))
            // ... 나머지 필드들
            .build();

        termRepository.save(term);                      // ④ DB 저장 (UPSERT)
    }
}
```

### MyBatis와 비교

```
MyBatis 방식:
  ① API 호출 → JSON 응답
  ② JSON → VO 변환 (수동 setter or ObjectMapper)
  ③ mapper.insertTerm(termVO) 또는 mapper.updateTerm(termVO)
  → INSERT와 UPDATE를 구분해서 호출해야 함

JPA 방식:
  ① API 호출 → 암호문 응답
  ② 복호화 → JSON → Entity 변환
  ③ termRepository.save(term)
  → save() 하나로 INSERT/UPDATE 자동 판단!
  → PK(termCd)가 DB에 있으면 UPDATE, 없으면 INSERT
```

---

## 7. 동기화 유형별 API

### 4가지 동기화 대상

| type | API URL | 데이터 |
|------|---------|--------|
| term | /vc/api/sync/term | 학기 (2026-1학기, 2학기 등) |
| crs | /vc/api/sync/crs | 과목 (프로그래밍, 수학 등) |
| users | /vc/api/sync/users | 사용자 (학생, 교수 5만명+) |
| crsUsers | /vc/api/sync/crsUsers | 수강생 (과목-학생 매핑) |

!!! warning "순서"
    term → crs → users → crsUsers (의존성 순서!)

### 왜 이 순서야?

```
crsUsers(수강생)가 존재하려면 → crs(과목)과 users(사용자)가 먼저 있어야 해
crs(과목)이 존재하려면 → term(학기)이 먼저 있어야 해

term → crs → users → crsUsers

거꾸로 하면?
  crsUsers 저장할 때 참조할 과목/사용자가 없어 → 에러!
```

### 페이징이 필요한 유형

```
term:     학기 → 2~4개. 페이징 불필요 (1페이지면 충분)
crs:      과목 → 수백~수천 개. 페이징 필요할 수 있음
users:    사용자 → 5만 명+. 페이징 필수! (52페이지)
crsUsers: 수강생 → 수만~수십만. 페이징 필수!
```

---

## 8. 에러 처리와 로깅

### SyncLog Entity

```java
// 동기화 결과를 기록하는 Entity
@Entity
@Table(name = "TB_NEXCLASS_SYNC_LOG")
public class SyncLog {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long syncLogId;        // PK (자동 증가)

    private String syncType;       // "term", "crs", "users", "crsUsers"
    private String syncStatus;     // "PROCESSING", "SUCCESS", "FAILED"
    private Integer totalCount;    // 동기화된 데이터 수
    private String errorMessage;   // 실패 시 에러 메시지
    private LocalDateTime syncStartedAt;   // 시작 시각
    private LocalDateTime syncCompletedAt; // 완료 시각
    private LocalDateTime createdAt;       // 로그 생성 시각
}
```

### 왜 로그를 DB에 저장해?

```
파일 로그만 있으면:
  → "어제 동기화 성공했어?" → 로그 파일 뒤져야 함
  → "이번 달 실패 몇 번이야?" → grep 해야 함

DB 로그가 있으면:
  → SELECT * FROM TB_NEXCLASS_SYNC_LOG WHERE sync_status = 'FAILED'
  → 대시보드에서 바로 조회 가능
  → 통계, 모니터링, 알림 연동 가능
```

---

## 9. 전체 흐름 최종 정리

**[매일 새벽 2시 자동 실행 (또는 수동 API 호출)]**

```mermaid
graph TD
    START["LmsSyncService.syncAll()"]
    S1["① SyncLog 생성<br/>status: PROCESSING"]
    S2["② syncTerms()<br/>JWT 생성 → POST /vc/api/sync/term<br/>→ AES 복호화 → JSON → Term Entity → save()"]
    S3["③ syncCourses()<br/>JWT 생성 → POST /vc/api/sync/crs<br/>→ AES 복호화 → JSON → Course Entity → save()"]
    S4["④ syncUsers() ← 페이징 필요! (52페이지)<br/>JWT 생성 → POST /vc/api/sync/users<br/>→ page 0, 1, 2, ... 51 반복"]
    S5["⑤ syncCourseUsers() ← 페이징 필요!<br/>JWT 생성 → POST /vc/api/sync/crsUsers<br/>→ 반복"]
    S6["⑥ SyncLog 업데이트<br/>성공: status=SUCCESS, totalCount=N<br/>실패: status=FAILED, errorMessage=..."]

    START --> S1 --> S2 --> S3 --> S4 --> S5 --> S6
```

---

## 10. 정리

| 단계 | 기술 | 코드 위치 |
|------|------|-----------|
| JWT 생성 | jjwt 라이브러리, HS256 | LmsSyncService.generateToken() |
| API 호출 | RestClient, Bearer 인증 | LmsSyncService.callLmsApi() |
| 복호화 | AES/CBC/PKCS5Padding | AES256Util.decrypt() |
| JSON 파싱 | Jackson ObjectMapper | LmsSyncService.processResponse() |
| DB 저장 | JPA repository.save() | LmsSyncService.syncTerms() 등 |
| 로그 기록 | SyncLog Entity | LmsSyncService.syncAll() |

**이 챕터에서 반드시 기억할 것**:
- 전체 흐름: **JWT 생성 → API 호출 → AES 복호화 → JSON 파싱 → DB 저장**
- 동기화 순서: **term → crs → users → crsUsers** (의존성!)
- users/crsUsers는 **페이징 필수** (데이터가 많으니까)
- SyncLog로 **동기화 결과를 추적**한다

---

### 확인 문제 (5문제)

> 다음 문제를 풀어봐. 답 못 하면 위에서 다시 읽어.

**Q1.** NexClass→LMS API 호출의 전체 흐름을 5단계로 말해봐.

**Q2.** 동기화 순서가 term → crs → users → crsUsers인 이유는?

**Q3.** application.properties에서 `nexclass.api.secret`과 `lms.sync.aes-key`는 각각 어디서 쓰여?

**Q4.** `repository.save(term)`이 INSERT를 할지 UPDATE를 할지 어떻게 판단해?

**Q5.** SyncLog를 파일이 아닌 DB에 저장하는 이유 3가지를 말해봐.

??? success "정답 보기"
    **A1.**

    1. JWT 생성 (APP_KEY + SECRET_KEY로 토큰 만듦)
    2. API 호출 (Authorization: Bearer {JWT} 헤더에 넣고 POST 요청)
    3. AES 복호화 (암호문 → JSON)
    4. JSON 파싱 (JSON → List&lt;Map&gt;)
    5. DB 저장 (Map → Entity → repository.save())

    **A2.** 의존성 때문에. crsUsers(수강생)는 crs(과목)과 users(사용자)를 참조해야 해서 먼저 있어야 하고, crs(과목)은 term(학기)을 참조해야 해서 먼저 있어야 해.

    **A3.** `nexclass.api.secret`: JWT Signature 생성 시 HMAC-SHA256의 비밀 키로 사용. `lms.sync.aes-key`: AES256Util 생성자에 전달되어 복호화 키와 IV로 사용.

    **A4.** PK(Primary Key) 기준으로 판단. termCd가 DB에 이미 있으면 UPDATE, 없으면 INSERT. JPA의 save()가 자동으로 처리해줌.

    **A5.**

    1. SQL로 바로 조회 가능 (파일은 grep 해야 함)
    2. 대시보드에서 동기화 현황 모니터링 가능
    3. 통계/알림 연동 가능 (실패 시 알림 등)
