# 04. JWT 생성과 검증 - Beta

---

> 👹 "구조 알았으니까 이제 진짜야. 토큰이 어떻게 만들어지고, 어떻게 확인되는지.
> 이거 모르면 코드 읽을 때 뭐가 뭔지 모를 거야."

---

## 1. 전체 흐름 - "만들고, 보내고, 확인한다"

```mermaid
graph TD
    S1["[1단계] NexClass가 JWT 생성<br/>APP_KEY + SECRET_KEY로 토큰을 만든다"]
    S2["[2단계] HTTP 요청에 JWT 첨부<br/>Authorization 헤더에 토큰을 넣어서 보낸다"]
    S3["[3단계] LMS가 JWT 검증<br/>SECRET_KEY로 서명 확인 + 만료 확인"]
    S4{"통과?"}
    OK["데이터 응답"]
    FAIL["401 Unauthorized"]
    S1 --> S2 --> S3 --> S4
    S4 -->|Yes| OK
    S4 -->|No| FAIL
```

---

## 2. [1단계] JWT 생성 - "토큰 만들기"

### 재료

```
필요한 것:
  1. APP_KEY = "knu-lms-2026"        ← Payload에 넣을 데이터
  2. SECRET_KEY = "KnuLmsSecretKey2026!@#0123456789"  ← 서명용 비밀 키
  3. 알고리즘 = HS256                ← Header에 명시
  4. 만료시간 = 현재 + 30분          ← Payload에 넣을 데이터
```

### 단계별 과정

```mermaid
graph TD
    H1["Step 1: Header JSON<br/>{&quot;alg&quot;:&quot;HS256&quot;,&quot;typ&quot;:&quot;JWT&quot;}"]
    H2["Base64 인코딩 → eyJhbGci..."]
    P1["Step 2: Payload JSON<br/>{&quot;appKey&quot;:&quot;knu-lms-2026&quot;,&quot;iat&quot;:170..,&quot;exp&quot;:170..}"]
    P2["Base64 인코딩 → eyJhcHBL..."]
    SIG["Step 3: 서명 만들기<br/>Header.Payload + SECRET_KEY<br/>→ HMAC-SHA256 → SflKxwRJ..."]
    JWT["Step 4: 합치기<br/>Header . Payload . Signature<br/>= 최종 JWT 토큰"]

    H1 --> H2
    P1 --> P2
    H2 --> SIG
    P2 --> SIG
    SIG --> JWT
    H2 --> JWT
    P2 --> JWT
```

### Java 코드로 보면

```java
// jjwt 라이브러리 사용 (우리 프로젝트 pom.xml에 있음)

// 재료 준비
String appKey = "knu-lms-2026";
String secretKey = "KnuLmsSecretKey2026!@#0123456789";

// JWT 생성
String token = Jwts.builder()
    .claim("appKey", appKey)           // Payload에 appKey 넣기
    .issuedAt(new Date())              // Payload에 iat (발급시각) 넣기
    .expiration(                       // Payload에 exp (만료시각) 넣기
        new Date(System.currentTimeMillis() + 1800000)  // 30분 뒤
    )
    .signWith(                         // Signature 만들기
        Keys.hmacShaKeyFor(secretKey.getBytes()),  // SECRET_KEY
        Jwts.SIG.HS256                             // 알고리즘
    )
    .compact();                        // Header.Payload.Signature 합치기

// 결과: "eyJhbGci...eyJhcHBL...SflKxwRJ..."
```

**한 줄씩 뭐 하는 거야?**

| 코드 | 하는 일 | JWT 어디에? |
|------|---------|------------|
| `Jwts.builder()` | JWT 만들기 시작 | - |
| `.claim("appKey", appKey)` | appKey 클레임 추가 | Payload |
| `.issuedAt(new Date())` | 발급 시각 추가 | Payload.iat |
| `.expiration(...)` | 만료 시각 추가 | Payload.exp |
| `.signWith(...)` | SECRET_KEY로 서명 | Signature |
| `.compact()` | 3조각 합쳐서 문자열로 | Header.Payload.Signature |

---

## 3. [2단계] HTTP 요청에 JWT 첨부 - "신분증 보여주기"

### Authorization 헤더

```
POST /vc/api/sync/term?orgCd=ORG0000001 HTTP/1.1
Host: www.knu10.cc
Content-Type: application/json
Authorization: Bearer eyJhbGci...eyJhcHBL...SflKxwRJ...
                ^^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                접두어   JWT 토큰
```

### Bearer가 뭐야?

```
"Bearer" = "소지자"

"이 토큰을 가지고 있는 놈이 인증된 사용자야"
라는 뜻의 표준 접두어.

왜 붙여?
→ HTTP 인증에는 여러 방식이 있거든.
   Basic, Bearer, Digest, etc.
→ "Bearer"라고 써야 서버가 "아 JWT구나" 알아.
```

### Java 코드로 보면

```java
// RestClient로 HTTP 요청 보내기 (Spring Boot 4.x)

String response = restClient.post()
    .uri("https://www.knu10.cc/vc/api/sync/term?orgCd=ORG0000001")
    .header("Authorization", "Bearer " + token)  // ← JWT 첨부
    .contentType(MediaType.APPLICATION_JSON)
    .body(requestBody)
    .retrieve()
    .body(String.class);
```

---

## 4. [3단계] JWT 검증 - "신분증 확인하기"

### LMS 서버가 하는 일

!!! abstract "LMS 서버 JWT 검증 흐름"
    **① Authorization 헤더에서 "Bearer " 떼고 토큰 추출**
    "Bearer eyJhbGci..." → "eyJhbGci..."

    **② 토큰을 점(.)으로 분리**
    Header / Payload / Signature

    **③ 서명 검증**
    Header + Payload + SECRET_KEY → HMAC-SHA256
    → 계산한 서명 vs 토큰의 서명 비교
    → 다르면? 401 Unauthorized (위조!)

    **④ 만료 검증**
    Payload의 exp vs 현재 시각
    → exp < 현재? 401 Unauthorized (만료!)

    **⑤ 클레임 확인**
    appKey가 등록된 앱인지?
    → 아니면? 401 Unauthorized (미등록!)

    **⑥ 전부 통과 → 요청 처리 → 데이터 응답**

### 검증 실패하면?

| 실패 원인 | 응답 | 의미 |
|-----------|------|------|
| 서명 불일치 | 401 | 토큰이 위조됐거나 SECRET_KEY가 다름 |
| 만료됨 | 401 | 토큰 유효기간 지남. 새로 발급 필요. |
| appKey 미등록 | 401 | 등록 안 된 앱이 호출함 |
| 토큰 형식 오류 | 400 | JWT 형식 자체가 잘못됨 |
| 토큰 없음 | 401 | Authorization 헤더가 없음 |

---

## 5. 전체 시퀀스 다이어그램

```mermaid
sequenceDiagram
    participant N as NexClass
    participant L as LMS
    N->>N: ① JWT 생성 (appKey + secretKey)
    N->>L: ② POST /vc/api/sync/term<br/>Authorization: Bearer {JWT}
    L->>L: ③ JWT 검증<br/>서명 확인 / 만료 확인 / 앱키 확인
    L->>L: ④ 데이터 조회
    L->>L: ⑤ AES-256 암호화
    L-->>N: ⑥ 암호화된 응답
    N->>N: ⑦ AES-256 복호화
    N->>N: ⑧ JSON 파싱
    N->>N: ⑨ Entity 변환 → DB 저장
```

MyBatis 시절이랑 비교하면:

```
MyBatis (같은 시스템 안):
  브라우저 → 서버 → DB 조회 → 응답
  (세션으로 인증. 간단.)

NexClass → LMS (다른 시스템):
  NexClass → JWT 생성 → HTTP 요청 → LMS가 JWT 검증 → 데이터 조회
  → AES 암호화 → 응답 → NexClass가 복호화 → 저장
  (JWT + AES. 복잡하지만 보안 때문에 필요.)
```

---

## 6. 주의사항 / 함정

### 함정 1: "토큰 한 번 만들면 계속 쓸 수 있지?"

```
❌ 만료 시간(exp)이 있어.
   30분 지나면 못 써. 새로 만들어야 해.
   동기화 작업이 30분 넘으면? 중간에 토큰 새로 발급.
```

### 함정 2: "Bearer 안 붙이면?"

```
❌ LMS 서버가 인증 방식을 모르게 돼.
   "Authorization: eyJhbGci..." → 실패
   "Authorization: Bearer eyJhbGci..." → 성공
   표준이야. 꼭 붙여.
```

### 함정 3: "SECRET_KEY를 코드에 하드코딩해도 되지?"

```
❌ 코드가 GitHub에 올라가면? SECRET_KEY 노출.
   → 설정 파일(application.properties)에 넣고
   → .gitignore로 관리하거나
   → 환경변수로 주입.

   우리 프로젝트:
   application.properties에 nexclass.api.secret=KnuLmsSecretKey2026!@#0123456789
   → @Value("${nexclass.api.secret}") 로 주입
```

### 함정 4: "검증은 LMS가 하니까 NexClass는 신경 안 써도 되지?"

```
△ 반은 맞고 반은 틀려.
   검증 자체는 LMS가 하는 게 맞아.
   근데 NexClass도 "토큰이 만료됐는지" 정도는 체크해야 해.
   만료된 토큰 보내봤자 401 오니까, 먼저 확인하고 재발급하는 게 효율적.
```

---

## 7. 정리

| 단계 | 누가 | 뭘 하는지 |
|------|------|-----------|
| 생성 | NexClass | APP_KEY + SECRET_KEY → JWT 토큰 만듦 |
| 전송 | NexClass | HTTP 헤더에 `Bearer {token}` 첨부해서 보냄 |
| 검증 | LMS | 서명 확인 → 만료 확인 → 앱키 확인 |
| 결과 | LMS | 통과→데이터 응답 / 실패→401 |

**이 챕터에서 반드시 기억할 것**:
- JWT는 **생성 → 전송 → 검증** 3단계
- 생성은 NexClass, 검증은 LMS가 한다
- `Authorization: Bearer {token}` 형식으로 HTTP 헤더에 넣는다
- 만료되면 새로 만들어야 한다

---

### 확인 문제 (4문제)

> 다음 문제를 풀어봐. 답 못 하면 위에서 다시 읽어.

**Q1.** JWT 생성에 필요한 재료 4가지를 말해봐.

**Q2.** `Jwts.builder().claim("appKey", appKey).signWith(...)` 에서 `.claim()`은 JWT 3조각 중 어디에 들어가? `.signWith()`는?

**Q3.** Authorization 헤더에 "Bearer "를 빼고 토큰만 보내면 어떻게 돼?

**Q4.** JWT가 만료됐을 때 LMS는 뭘 응답하고, NexClass는 어떻게 해야 해?

??? success "정답 보기"
    **A1.** APP_KEY (Payload 데이터), SECRET_KEY (서명용 키), 알고리즘 (HS256, Header에 명시), 만료시간 (Payload.exp).

    **A2.** `.claim("appKey", appKey)`는 **Payload**에 들어가. `.signWith(...)`는 **Signature** 생성에 사용돼.

    **A3.** LMS 서버가 인증 방식을 식별 못 해서 실패해. Bearer는 "이건 JWT 인증이야"라고 알려주는 표준 접두어야. 빼면 토큰 파싱 자체를 안 해.

    **A4.** LMS는 401 Unauthorized를 응답해. NexClass는 새 JWT를 생성해서 재요청해야 해. 만료된 토큰을 계속 보내봤자 계속 401만 와.
