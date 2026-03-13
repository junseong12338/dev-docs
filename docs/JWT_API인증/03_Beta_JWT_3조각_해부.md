# 03. JWT 3조각 해부 - Beta

---

> 👹 "JWT 구조? Header.Payload.Signature. 끝.
> ...이라고 대답하면 불합격이야. 각 조각이 뭘 하는지, 왜 그렇게 생겼는지 다 설명해봐."

---

## 1. 전체 구조 - "점(.) 3개로 나뉜다"

JWT는 이렇게 생겼어:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBLZXkiOiJrbnUtbG1zLTIwMjYiLCJpYXQiOjE3MDkwMjExMDAsImV4cCI6MTcwOTAyMjkwMH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

읽을 수 있어? 못 읽지. 근데 점(`.`)으로 나눠보면:

```
조각 1: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9           ← Header
조각 2: eyJhcHBLZXkiOiJrbnUtbG1zLTIwMjYiLCJp...       ← Payload
조각 3: SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c   ← Signature
```

```mermaid
graph LR
    H["Header (헤더)<br/>Base64 인코딩<br/>(누구나 읽음)"]
    P["Payload (내용물)<br/>Base64 인코딩<br/>(누구나 읽음)"]
    S["Signature (서명)<br/>HMAC-SHA256 해시<br/>(위조 방지)"]
    H --- |"."| P --- |"."| S
```

---

## 2. Header (헤더) - "이 토큰 어떻게 만들었는지"

### 원본 JSON

```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### 각 필드

| 필드 | 뜻 | 값 | 설명 |
|------|-----|-----|------|
| `alg` | algorithm | `HS256` | 서명에 사용한 알고리즘 |
| `typ` | type | `JWT` | 토큰 타입 |

### alg (알고리즘) 종류

```
HS256 = HMAC + SHA-256      ← 대칭키 (같은 키로 서명/검증)
RS256 = RSA + SHA-256       ← 비대칭키 (비밀키로 서명, 공개키로 검증)
ES256 = ECDSA + SHA-256     ← 비대칭키 (더 짧은 키 길이)
```

**우리 프로젝트**: HS256 사용. NexClass와 LMS가 같은 SECRET_KEY를 공유하니까 대칭키 방식.

### Base64로 인코딩되면?

```
{"alg": "HS256", "typ": "JWT"}
         ↓ Base64 인코딩
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
         ↓ Base64 디코딩 (누구나 가능!)
{"alg": "HS256", "typ": "JWT"}
```

---

## 3. Payload (페이로드) - "실제 데이터"

### 원본 JSON (우리 프로젝트 기준)

```json
{
  "appKey": "knu-lms-2026",
  "iat": 1709021100,
  "exp": 1709022900
}
```

### 각 필드

| 필드 | 뜻 | 값 | 설명 |
|------|-----|-----|------|
| `appKey` | Application Key | `knu-lms-2026` | "나 NexClass야" 식별 |
| `iat` | Issued At | `1709021100` | 토큰 발급 시각 (Unix 타임스탬프) |
| `exp` | Expiration | `1709022900` | 토큰 만료 시각 (Unix 타임스탬프) |

### Claim (클레임) 이란?

Payload 안의 각 필드를 **Claim(클레임)**이라고 불러. "주장"이라는 뜻이야.

```
"나는 knu-lms-2026이라는 앱이야" ← appKey 클레임
"이 토큰은 이 시각에 발급됐어"   ← iat 클레임
"이 토큰은 이 시각에 만료돼"     ← exp 클레임
```

### 클레임 3종류

!!! note "클레임 3종류"
    **1. 등록된 클레임 (Registered)** - JWT 표준에서 정한 것

    - `iss` (issuer) = 발급자
    - `sub` (subject) = 대상
    - `aud` (audience) = 수신자
    - `exp` (expiration) = 만료 시각
    - `iat` (issued at) = 발급 시각
    - `nbf` (not before) = 이 시각 전에는 무효
    - `jti` (JWT ID) = 토큰 고유 ID

    **2. 공개 클레임 (Public)** - 충돌 방지를 위해 URI로 정의

    - 거의 안 쓰임. 알 필요 없어.

    **3. 비공개 클레임 (Private)** - 서버끼리 약속한 것

    - `appKey` = "knu-lms-2026" -- 이거! 우리가 정한 거
    - `role` = "ADMIN" -- 이런 것도 가능

### Unix 타임스탬프?

```
"1709021100"이 뭔데?

1970년 1월 1일 00:00:00 (UTC)부터 경과한 초(seconds) 수.

1709021100 = 2024년 2월 27일 12:05:00

왜 이렇게 써?
→ 시간대(timezone) 상관없이 전 세계가 같은 숫자를 쓸 수 있으니까.
→ 컴퓨터가 비교하기 쉬우니까. (큰 숫자 = 미래)
```

### ⚠️ Payload에 넣으면 안 되는 것

```
❌ 비밀번호       → Base64 디코딩하면 바로 보여
❌ 주민등록번호   → 누구나 읽을 수 있다고
❌ 카드번호       → 진짜 개인정보 유출이야
❌ 큰 데이터      → 토큰 크기가 커져서 매 요청마다 대역폭 낭비

✅ 사용자 ID, 앱 키, 권한, 만료시간 정도만 넣어.
```

---

## 4. Signature (서명) - "위조 방지 도장"

### 이게 핵심이야

Header와 Payload는 누구나 읽을 수 있잖아. 그러면 누가 Payload를 바꿔치기하면?

```
공격자가 이렇게 바꾸면?

원본: {"appKey": "knu-lms-2026", "exp": 1709022900}
위조: {"appKey": "knu-lms-2026", "exp": 9999999999}  ← 만료 안 되게!
```

**서명이 이걸 막아.**

### 서명 생성 과정

```
HMAC-SHA256(
  Base64(Header) + "." + Base64(Payload),   ← 서명할 대상
  SECRET_KEY                                 ← 비밀 키
)
= 서명값
```

단계별로:

```
1. Header를 Base64 인코딩  → "eyJhbGci..."
2. Payload를 Base64 인코딩 → "eyJhcHBL..."
3. 둘을 점(.)으로 연결     → "eyJhbGci...eyJhcHBL..."
4. SECRET_KEY와 함께 HMAC-SHA256 해싱
5. 결과 = 서명값           → "SflKxwRJ..."
```

### 검증 과정 (LMS 서버가 하는 일)

!!! abstract "검증 과정 (LMS 서버가 하는 일)"
    NexClass가 보낸 JWT: Header.Payload.Signature

    **LMS 서버:**

    1. Header와 Payload를 꺼냄
    2. 자기가 가진 SECRET_KEY로 서명을 다시 만듦
    3. 다시 만든 서명 vs 토큰에 붙어있는 서명 비교
        - 같다 → "위조 안 됐네. 통과!"
        - 다르다 → "누가 건드렸네. 거부!" (401)
    4. exp 확인 → 현재시간보다 이전이면 만료 (401)

### 왜 위조가 안 되는 거야?

```
공격자가 Payload를 바꾸면?
→ Payload가 바뀌었으니 서명도 달라져야 해
→ 근데 서명을 만들려면 SECRET_KEY가 필요해
→ 공격자는 SECRET_KEY를 몰라
→ 서명을 못 만들어 → 검증 실패 → 거부!

공격자가 서명도 바꾸면?
→ SECRET_KEY 없이 만든 서명은 검증 실패
→ 결국 SECRET_KEY 없으면 유효한 토큰을 못 만들어
```

**이래서 SECRET_KEY가 절대 노출되면 안 되는 거야.**

---

## 5. 전체 흐름 다이어그램

**NexClass에서 JWT 만들기:**

```mermaid
graph TD
    H["Header JSON"] -->|Base64| HE["eyJhbGci..."]
    P["Payload JSON"] -->|Base64| PE["eyJhcHBL..."]
    HE --> MERGE["합치기: eyJhbGci...eyJhcHBL..."]
    PE --> MERGE
    MERGE --> HMAC["HMAC-SHA256"]
    SK["SECRET_KEY"] --> HMAC
    HMAC --> SIG["서명값: SflKxwRJ..."]
    HE --> JWT["최종 JWT: Header . Payload . Signature"]
    PE --> JWT
    SIG --> JWT
```

**LMS에서 JWT 검증하기:**

```mermaid
graph TD
    JWT["받은 JWT"] --> SPLIT["Header, Payload 분리"]
    SPLIT --> RESIGN["Header + Payload + SECRET_KEY → HMAC-SHA256 → 새 서명"]
    SPLIT --> COMPARE["받은 서명과 새 서명 비교"]
    RESIGN --> COMPARE
    COMPARE -->|같으면| EXP["exp 확인 → 통과!"]
    COMPARE -->|다르면| REJECT["거부! (401)"]
```

---

## 6. 주의사항 / 함정

### 함정 1: "Payload를 암호화해서 보내는 거 아냐?"

```
❌ Payload는 암호화가 아니라 Base64 인코딩.
   jwt.io에서 바로 읽을 수 있어.
   비밀 데이터 넣으면 큰일 나.
```

### 함정 2: "서명이 있으니까 내용을 못 읽잖아?"

```
❌ 서명은 "못 읽게" 하는 게 아니라 "못 바꾸게" 하는 거야.
   읽기 → 누구나 가능
   바꾸기 → SECRET_KEY 없으면 불가능
```

### 함정 3: "토큰이 길면 보안이 좋은 거 아냐?"

```
❌ 토큰 길이 = Payload 크기.
   긴 토큰 = 데이터를 많이 넣었다는 뜻이지, 보안이 좋다는 뜻이 아냐.
   오히려 매 요청마다 큰 토큰을 보내면 대역폭 낭비.
```

### 함정 4: "SECRET_KEY 대신 APP_KEY로 서명하면?"

```
❌ APP_KEY는 공개 정보야. 누구한테 말해도 상관없어.
   SECRET_KEY는 비밀이야. 노출되면 누구나 유효한 JWT를 만들 수 있어.

   APP_KEY = 네 이름 (공개)
   SECRET_KEY = 네 비밀번호 (비밀)
```

---

## 7. 정리

| 조각 | 내용 | 인코딩 방식 | 누가 읽어? | 목적 |
|------|------|------------|-----------|------|
| Header | 알고리즘, 타입 | Base64 | 누구나 | "이 토큰 어떻게 만들었는지" |
| Payload | 클레임 (앱키, 만료 등) | Base64 | 누구나 | "실제 데이터" |
| Signature | 해시값 | HMAC-SHA256 | 검증만 가능 | "위조 방지" |

**이 챕터에서 반드시 기억할 것**:
- Header/Payload는 **누구나 읽을 수 있다** (인코딩일 뿐)
- Signature가 **위조를 막아준다** (SECRET_KEY 없으면 서명 생성 불가)
- SECRET_KEY는 **절대 노출하면 안 된다**

---

### 확인 문제 (5문제)

> 다음 문제를 풀어봐. 답 못 하면 위에서 다시 읽어.

**Q1.** JWT의 3조각 이름과 각각의 역할을 말해봐.

**Q2.** Payload에 `"exp": 1709022900`이 있어. 현재 Unix 타임스탬프가 `1709023000`이야. 이 토큰은 유효해?

**Q3.** 공격자가 Payload의 만료시간을 바꿨어. LMS 서버는 이걸 어떻게 알아차려?

**Q4.** APP_KEY와 SECRET_KEY의 차이가 뭐야? 둘 다 노출되면 뭐가 문제야?

**Q5.** HS256에서 "같은 키로 서명/검증"한다는 게 구체적으로 무슨 뜻이야?

??? success "정답 보기"
    **A1.**

    - Header: 알고리즘/타입 정보. "이 토큰 어떻게 만들었는지" 알려줌.
    - Payload: 실제 데이터(클레임). 앱키, 발급시각, 만료시각 등.
    - Signature: HMAC-SHA256 해시값. 위조 방지 도장.

    **A2.** 무효(만료)야. exp(1709022900) < 현재(1709023000)이니까 만료 시각을 지났어. LMS 서버는 401을 돌려보내.

    **A3.** LMS 서버가 Header+Payload를 자기 SECRET_KEY로 서명을 다시 만들어. Payload가 바뀌었으니 서명값이 달라져. 토큰에 붙어있는 원래 서명과 비교하면 불일치 → 위조 감지 → 거부.

    **A4.** APP_KEY는 "나 누구야" 식별용 공개 정보. SECRET_KEY는 서명 생성/검증에 쓰는 비밀 정보. APP_KEY가 노출되면 "누가 호출하는지" 알려지는 정도지만, SECRET_KEY가 노출되면 공격자가 유효한 JWT를 직접 만들 수 있어 → 인증 시스템 완전 뚫림.

    **A5.** NexClass가 SECRET_KEY로 서명을 만들어(생성). LMS가 같은 SECRET_KEY로 서명을 다시 만들어서 비교해(검증). 양쪽이 같은 키를 공유하고 있어야만 동작하는 구조야. 그래서 "대칭키" 방식이라고 해.
