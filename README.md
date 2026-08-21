# TODO App

FastAPI + SQLite로 만든 간단한 할 일(TODO) 관리 앱입니다.
백엔드 API와 정적 프론트엔드(브라우저 UI)를 한 서버에서 함께 제공합니다.
이메일/비밀번호로 회원가입·로그인하며(JWT), 할 일은 **사용자별로 격리**됩니다.

## 기능

| 기능 | 설명 |
| --- | --- |
| 회원가입 / 로그인 | 이메일 + 비밀번호, JWT 발급 (유효기간 7일) |
| 사용자별 격리 | 로그인한 사용자 본인의 할 일만 조회·수정·삭제 가능 |
| 할 일 추가 | 날짜 + 내용으로 등록 (날짜 미지정 시 오늘) |
| 내용 수정 | 할 일 내용(content) 변경 |
| 날짜 수정 | 달력에서 날짜 선택 시 변경 |
| 완료 / 완료 취소 | 체크박스로 완료 처리하거나 다시 미완료로 되돌림 |
| 할 일 삭제 | DB에서 해당 항목 제거 |
| 오늘 할 일 | 오늘 날짜의 할 일 (내용 오름차순 정렬) |
| 다가오는 할 일 | 내일부터 7일간(오늘 미포함), 날짜→내용 순 정렬 |
| 밀린 할 일 | 오늘 이전의 미완료 항목, 날짜→내용 순 정렬 |
| 날짜별 조회 | 특정 날짜의 할 일 (내용 오름차순 정렬) |

프론트엔드는 각 항목의 `⋯` 메뉴에서 **할일 수정 / 날짜 수정 / 삭제**를 할 수 있습니다.

## 인증

이메일 + 비밀번호로 가입/로그인하고, 발급받은 **JWT를 `Authorization: Bearer` 헤더**로
보냅니다. 쿠키는 쓰지 않으며, 프론트엔드는 토큰을 `localStorage`에 보관합니다.
서버는 세션 상태를 저장하지 않으므로(stateless) 로그아웃은 토큰을 버리는 것으로 끝납니다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/auth/register` | 회원가입 (`email`, `password`, `code`) |
| `POST` | `/auth/jwt/login` | 로그인 → `access_token` 발급 (**form 인코딩**, 필드명 `username`) |
| `GET` | `/users/me` | 로그인한 본인 정보 |
| `PATCH` | `/users/me` | 본인 이메일/비밀번호 변경 |
| `GET` | `/auth/config` | 회원가입에 초대 코드가 필요한지 여부 (프론트 UI용) |

### 환경변수 설정 (`.env`)

설정값은 프로젝트 폴더의 **`.env` 파일**에 적어둡니다. `./run.sh`와 `docker compose`가
모두 이 파일을 자동으로 읽으므로, 터미널을 새로 열어도 다시 입력할 필요가 없습니다.

```bash
cp .env.example .env          # 템플릿 복사
openssl rand -base64 32       # 출력값을 JWT_SECRET에 붙여넣기
```

`.env` 예시:

```bash
JWT_SECRET="KfsIdTGxTJQ7Rp/S24udziAmULQbVr7xN3pKrMBudeo="
REGISTER_CODE="원하는초대코드"
```

`.env`는 `.gitignore`·`.dockerignore`에 등록되어 **커밋되지도, 이미지에 들어가지도
않습니다.** 값을 바꾸면 `./run.sh`를 다시 실행하면 적용됩니다.

| 변수 | 필수 | 설명 |
| --- | --- | --- |
| `JWT_SECRET` | 운영에서 필수 | JWT 서명 키. **미설정 시 임시 키를 생성하므로 서버 재시작 때마다 전원 로그아웃**됩니다. 값을 바꾸면 기존 토큰이 전부 무효가 됩니다(계정·데이터는 그대로). |
| `REGISTER_CODE` | 권장 | 설정하면 회원가입 시 이 초대 코드가 필요합니다. 서버를 외부에 공개한다면 반드시 설정하세요. 한글·이모지도 쓸 수 있습니다. 이미 만든 계정에는 영향이 없습니다. |
| `DATABASE_URL` | 선택 | 기본값 `sqlite:///./todo.db` |

환경변수를 그때그때 직접 주는 것도 됩니다 — `JWT_SECRET=... ./run.sh`

비밀번호는 8자 이상이어야 하고, 이메일을 포함할 수 없습니다.

```bash
# 회원가입
curl -X POST localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"me@example.com","password":"secret1234","code":"초대코드"}'

# 로그인 → 토큰 획득 (form 인코딩, username에 이메일)
TOKEN=$(curl -s -X POST localhost:8000/auth/jwt/login \
  -d 'username=me@example.com&password=secret1234' | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')

# 이후 모든 /todos 호출에 토큰을 실어 보낸다
curl localhost:8000/todos -H "Authorization: Bearer $TOKEN"
```

> 인증 없이 `/todos`를 호출하면 `401`입니다. 남의 할 일 id로 요청하면 `403`이 아니라
> `404`를 반환합니다 — 그 id의 존재 여부 자체를 감추기 위함입니다.

## API 엔드포인트

아래 `/todos` 엔드포인트는 **모두 로그인이 필요**하며, 항상 본인 데이터만 다룹니다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `POST` | `/todos` | 할 일 추가 |
| `GET` | `/todos` | 조회 (쿼리 파라미터로 필터) |
| `PATCH` | `/todos/{id}` | 부분 수정 — `content` / `date` 중 보낸 필드만 변경 |
| `PATCH` | `/todos/{id}/done` | 완료 표시 |
| `PATCH` | `/todos/{id}/undone` | 완료 취소 |
| `DELETE` | `/todos/{id}` | 삭제 |

### `GET /todos` 쿼리 파라미터

| 파라미터 | 예시 | 설명 |
| --- | --- | --- |
| `date` | `?date=2026-06-26` | 특정 날짜 |
| `start` / `end` | `?start=2026-06-27&end=2026-07-03` | 기간 조회 (양끝 포함) |
| `done` | `?done=false` | 완료 여부 필터 |

조합도 가능합니다. 예) `GET /todos?date=2026-06-26&done=false` → 해당 날짜의 미완료만.

### 요청/응답 예시

```bash
# 추가
curl -X POST localhost:8000/todos \
  -H 'Content-Type: application/json' \
  -d '{"date":"2026-06-26","content":"보고서 작성"}'
# → {"id":1,"date":"2026-06-26","content":"보고서 작성","done":false}

# 내용만 수정
curl -X PATCH localhost:8000/todos/1 \
  -H 'Content-Type: application/json' -d '{"content":"보고서 검토"}'

# 날짜만 수정
curl -X PATCH localhost:8000/todos/1 \
  -H 'Content-Type: application/json' -d '{"date":"2026-07-01"}'

# 내용 + 날짜 함께 수정
curl -X PATCH localhost:8000/todos/1 \
  -H 'Content-Type: application/json' -d '{"content":"최종본","date":"2026-07-02"}'

# 완료 / 완료 취소
curl -X PATCH localhost:8000/todos/1/done
curl -X PATCH localhost:8000/todos/1/undone

# 기간 조회
curl 'localhost:8000/todos?start=2026-06-27&end=2026-07-03'

# 삭제
curl -X DELETE localhost:8000/todos/1
```

`PATCH /todos/{id}`는 부분 수정(PATCH 시맨틱)이라 보낸 필드만 바뀝니다.
API 문서(Swagger UI)는 서버 실행 후 `http://localhost:8000/docs` 에서 볼 수 있습니다.

## 기술 스택

- **FastAPI** — API 서버 + 정적 프론트엔드 서빙
- **SQLAlchemy 2.0 (async)** — ORM. fastapi-users의 SQLAlchemy 어댑터가 async 전용이라
  앱 전체가 `create_async_engine` + `aiosqlite`로 동작합니다(Alembic은 동기 드라이버 사용).
- **fastapi-users** — 회원가입/로그인, 비밀번호 해싱, JWT 발급·검증
- **Alembic** — DB 마이그레이션
- **SQLite** — 데이터 저장
- **바닐라 JS / HTML / CSS** — 프론트엔드 (`static/index.html`, 프레임워크 없음)

## 실행 방법

### 1) 로컬 (Python)

```bash
pip install -r requirements.txt   # 또는: uv pip install -r requirements.txt
cp .env.example .env              # JWT_SECRET / REGISTER_CODE 작성 (위 '환경변수 설정' 참고)

./run.sh            # .env 로드 → 마이그레이션 적용 → 서버 실행 (기본 포트 8000)
./run.sh 8765       # 포트 지정
```

`http://localhost:8000` 접속 → 웹 UI 사용.

### 2) Docker

```bash
docker compose up -d --build
```

- DB 파일은 이미지에 포함되지 않고 **named volume(`todo_data`)** 의 `/data/todo.db`에 저장되어, 컨테이너를 교체해도 데이터가 유지됩니다.
- 종료: `docker compose down` (데이터 유지) / `docker compose down -v` (데이터까지 삭제)

## 운영 서버 배포 (기존 데이터가 있는 서버에 인증 도입하기)

`todo.db`는 git에 올라가지 않으므로 `git pull`로 **데이터가 덮이지 않습니다.**
인증 도입 후 처음 배포할 때는 아래 순서를 따르세요.

```bash
cd ~/workspace/my_todo
git pull

# 1) 백업 — 이 마이그레이션은 SQLite 제약상 todos 테이블을 재생성합니다
cp todo.db "todo.db.bak.$(date +%Y%m%d%H%M)"

# 2) 새 의존성 설치 ★ git pull은 패키지를 설치하지 않습니다
#    이 단계를 건너뛰면 run.sh가 ModuleNotFoundError로 즉시 실패합니다
.venv/bin/pip install -r requirements.txt

# 3) .env 작성 — 서버를 띄우기 "전에" 해야 합니다
#    (REGISTER_CODE 없이 공개하면 남이 먼저 가입할 수 있습니다)
cp .env.example .env
openssl rand -base64 32      # 출력값을 .env의 JWT_SECRET에 넣기
vi .env

# 4) 서버 실행 — 마이그레이션이 적용되며 기존 할 일은 '소유자 없음' 상태가 됩니다
./run.sh

# 5) 브라우저에서 회원가입 (초대 코드 입력) → 로그인
#    이 시점에는 기존 할 일이 하나도 안 보이는 게 정상입니다

# 6) 기존 할 일을 본인 계정에 귀속
.venv/bin/python backfill_owner.py --email 내이메일@example.com --dry-run
.venv/bin/python backfill_owner.py --email 내이메일@example.com

# 7) 브라우저 새로고침 → 기존 할 일이 모두 보입니다
```

> **6번은 서버를 끄지 않아도 됩니다.** UPDATE 한 번이라 실행 중에 돌려도 되고,
> 끝난 뒤 브라우저를 새로고침하면 반영됩니다. 다만 확실히 하고 싶다면 끄고 해도 무해합니다.

주의할 점:

- **Python 3.10 이상**이 필요합니다 (`fastapi-users`, `pwdlib` 요구사항).
  `.venv/bin/python -V`로 확인하세요. 낮으면 venv를 다시 만들어야 합니다.
- 2번을 건너뛰면 `run.sh`의 `alembic upgrade head`가 `fastapi_users_db_sqlalchemy`를
  찾지 못해 실패합니다. **git pull 후 반드시 의존성을 설치하세요.**
- `.env`의 `JWT_SECRET`은 한 번 정하면 바꾸지 마세요. 바꾸면 발급된 토큰이 모두
  무효가 되어 다시 로그인해야 합니다(계정과 데이터는 그대로).
- 되돌리려면: `.venv/bin/alembic downgrade -1` (또는 백업 파일로 복원)

## DB 직접 조회

프론트/API를 거치지 않고 SQLite를 직접 조회하는 샘플 스크립트가 있습니다.

```bash
./query.sh                       # .venv 파이썬으로 ./todo.db 조회 (정렬된 박스 테이블 출력)
TODO_DB=/경로/다른.db ./query.sh  # 다른 DB 파일 지정
TODO_USER=me@example.com ./query.sh  # 특정 사용자의 할 일만
```

### 기존 데이터를 사용자에게 귀속시키기

인증을 도입하기 전에 쌓인 할 일은 `user_id`가 비어 있어 **어떤 사용자에게도 보이지
않습니다.** 먼저 회원가입을 하고, 그 이메일로 일괄 귀속시키세요.

```bash
.venv/bin/python backfill_owner.py --email me@example.com --dry-run  # 건수만 확인
.venv/bin/python backfill_owner.py --email me@example.com            # 실제 반영
```

## 프로젝트 구조

```
todo_app/
├── main.py             # FastAPI 앱 / 엔드포인트
├── auth.py             # fastapi-users 배선 (UserManager · JWT 전략 · 의존성)
├── database.py         # DB 엔진(async) · 세션
├── models.py           # SQLAlchemy 모델 (User, Todo)
├── schemas.py          # Pydantic 스키마 (Todo·User)
├── backfill_owner.py   # 소유자 없는 기존 할 일을 특정 사용자에게 귀속
├── migrations/         # Alembic 마이그레이션
├── static/index.html   # 프론트엔드 (바닐라 JS)
├── query_db.py         # DB 직접 조회 로직
├── query.sh            # query_db.py 실행 스크립트
├── run.sh              # 로컬 실행 스크립트 (.env 자동 로드)
├── .env.example        # 환경변수 템플릿 (.env는 커밋 안 됨)
├── Dockerfile
└── docker-compose.yml
```

## 데이터 모델

### `users`

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | int | PK (자동 증가) |
| `email` | str | 로그인 ID (unique) |
| `hashed_password` | str | 해싱된 비밀번호 (평문 저장 안 함) |
| `is_active` | bool | 활성 여부 — false면 로그인 불가 |
| `is_superuser` | bool | 관리자 여부 |
| `is_verified` | bool | 이메일 인증 여부 (현재 미사용) |

### `todos`

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | int | PK (자동 증가) |
| `user_id` | int? | 소유자 (`users.id`, `ON DELETE CASCADE`). NULL이면 앱에서 조회되지 않음 |
| `date` | date | 할 일 날짜 (`YYYY-MM-DD`) |
| `content` | str | 내용 |
| `done` | bool | 완료 여부 |
