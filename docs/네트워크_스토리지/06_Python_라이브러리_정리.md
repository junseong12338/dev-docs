# 06. Python 라이브러리 - 오늘 쓴 도구 뜯어보기

> 👹 "boto3 쓸 줄 아는 건 Lv1. 왜 boto3인지 아는 게 Lv2."

---

## 오늘 사용한 라이브러리

| 라이브러리 | 용도 | 어디서 썼는지 |
|-----------|------|-------------|
| **boto3** | AWS S3 호환 API | s3_upload.py (로컬→S3 업로드) |
| **paramiko** | SSH/SFTP 접속 | download_from_server.py (서버→로컬 다운) |
| **openpyxl** | Excel 파일 생성 | step5_all_weeks.py (분석 결과) |
| **urllib** | HTTP 요청 | step5_all_weeks.py (URL 상태 체크) |
| **concurrent.futures** | 병렬 처리 | step5_all_weeks.py (URL 동시 체크) |

---

## boto3 핵심 이해

```python
import boto3
from botocore.config import Config

s3 = boto3.client(
    "s3",
    endpoint_url="https://storage.gscdn.com",  # AWS가 아닌 커스텀 엔드포인트
    aws_access_key_id="a1a59c...",              # 인증: 누구인지
    aws_secret_access_key="edd018...",          # 인증: 서명 생성용
    region_name="us-east-1",                    # 리전 (GSCDN은 의미 없음)
    config=Config(s3={
        "addressing_style": "path"              # path style 강제!
    }),
)
```

### boto3가 내부에서 하는 일
```
s3.upload_file("local.mp4", "knu9", "tideflo/file.mp4")

내부 동작:
1. 파일 읽기
2. AWS Signature V4 서명 생성 (Secret Key 사용)
3. HTTP PUT 요청 생성
4. Authorization 헤더에 서명 첨부
5. https://storage.gscdn.com/knu9/tideflo/file.mp4 로 전송
6. 응답 코드 확인 (201 = 성공)
```

> 👹 boto3는 결국 **HTTP PUT 요청 + 인증 서명 자동화**야.
> curl로도 할 수 있지만, 서명 생성이 복잡해서 라이브러리 쓰는 거야.

---

## paramiko 핵심 이해

```python
import paramiko

# SSH 연결
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("49.247.41.199", port=22, username="tideflo", password="...")

# SFTP 세션 열기
sftp = ssh.open_sftp()

# 파일 다운로드
sftp.get("/voddata/.../abc.mp4", "C:/local/abc.mp4")

# 정리
sftp.close()
ssh.close()
```

### paramiko가 내부에서 하는 일
```
ssh.connect(...)

내부 동작:
1. TCP 연결 (49.247.41.199:22)
2. SSH 핸드셰이크 (암호화 방식 협상)
3. 호스트 키 확인 (서버가 진짜 그 서버인지)
4. 사용자 인증 (ID/PW)
5. 암호화된 터널 생성

sftp.get(remote, local)

내부 동작:
1. SSH 터널 위에서 SFTP 서브시스템 시작
2. OPEN 요청 (원격 파일 열기)
3. READ 요청 반복 (청크 단위 읽기)
4. 로컬 파일에 쓰기
5. CLOSE 요청
```

---

## 왜 이 라이브러리를 선택했는가

### S3 업로드: boto3 vs requests vs curl

| 방법 | 장점 | 단점 |
|------|------|------|
| **boto3** ✅ | S3 서명 자동처리, 에러 핸들링 | 설치 필요 |
| requests | 가벼움 | S3 서명 직접 구현해야 함 |
| curl | 설치 불필요 | 서명 구현 극악, 토큰 필요 |

### 서버 다운로드: paramiko vs subprocess+scp vs ftplib

| 방법 | 장점 | 단점 |
|------|------|------|
| **paramiko** ✅ | 자동화, 에러 핸들링, 이어받기 | 설치 필요 |
| subprocess+scp | 설치 불필요 | 비밀번호 자동입력 어려움 |
| ftplib | 내장 라이브러리 | FTP는 암호화 없음 |

> 👹 **도구 선택도 트레이드오프야.**
> "되니까 이거 씀"이 아니라, "이 상황에서 이게 최선이기 때문에"로 설명할 수 있어야 해.

---

## 👹 빠싺 검증 질문

- [ ] boto3의 endpoint_url이 왜 필요한지 설명 가능
- [ ] addressing_style: path가 왜 필요한지 설명 가능
- [ ] paramiko에서 SSH → SFTP 과정을 설명 가능
- [ ] boto3 대신 requests로 S3 업로드 하려면 뭘 직접 구현해야 하는지 알고 있다
- [ ] 각 라이브러리 선택 이유를 트레이드오프로 설명 가능
