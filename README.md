# TODO App

FastAPI + SQLite로 만든 간단한 할 일(TODO) 관리 앱입니다.
백엔드 API와 정적 프론트엔드(브라우저 UI)를 한 서버에서 함께 제공합니다.

## 기능

| 기능 | 설명 |
| --- | --- |
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

## API 엔드포인트

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
- **SQLAlchemy 2.0** — ORM
- **Alembic** — DB 마이그레이션
- **SQLite** — 데이터 저장
- **바닐라 JS / HTML / CSS** — 프론트엔드 (`static/index.html`, 프레임워크 없음)

## 실행 방법

### 1) 로컬 (Python)

```bash
pip install -r requirements.txt
./run.sh            # 마이그레이션 적용 후 서버 실행 (기본 포트 8000)
./run.sh 8765       # 포트 지정
```

`http://localhost:8000` 접속 → 웹 UI 사용.

### 2) Docker

```bash
docker compose up -d --build
```

- DB 파일은 이미지에 포함되지 않고 **named volume(`todo_data`)** 의 `/data/todo.db`에 저장되어, 컨테이너를 교체해도 데이터가 유지됩니다.
- 종료: `docker compose down` (데이터 유지) / `docker compose down -v` (데이터까지 삭제)

## DB 직접 조회

프론트/API를 거치지 않고 SQLite를 직접 조회하는 샘플 스크립트가 있습니다.

```bash
./query.sh                       # .venv 파이썬으로 ./todo.db 조회 (정렬된 박스 테이블 출력)
TODO_DB=/경로/다른.db ./query.sh  # 다른 DB 파일 지정
```

## 프로젝트 구조

```
todo_app/
├── main.py             # FastAPI 앱 / 엔드포인트
├── database.py         # DB 엔진 · 세션
├── models.py           # SQLAlchemy 모델 (Todo)
├── schemas.py          # Pydantic 스키마
├── migrations/         # Alembic 마이그레이션
├── static/index.html   # 프론트엔드 (바닐라 JS)
├── query_db.py         # DB 직접 조회 로직
├── query.sh            # query_db.py 실행 스크립트
├── run.sh              # 로컬 실행 스크립트
├── Dockerfile
└── docker-compose.yml
```

## 데이터 모델

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `id` | int | PK (자동 증가) |
| `date` | date | 할 일 날짜 (`YYYY-MM-DD`) |
| `content` | str | 내용 |
| `done` | bool | 완료 여부 |
