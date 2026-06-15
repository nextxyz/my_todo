FROM python:3.12-slim

WORKDIR /app

# 의존성을 먼저 설치해 레이어 캐시를 활용 (코드만 바뀌면 재설치 안 함)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사 (.dockerignore로 .venv / todo.db 등은 제외됨)
COPY . .

# DB 파일은 이미지가 아니라 볼륨(/data)에 둔다 → 컨테이너를 새로 띄워도 데이터 유지
ENV DATABASE_URL=sqlite:////data/todo.db
VOLUME ["/data"]

EXPOSE 8000

# 컨테이너 시작 시: 마이그레이션(없으면 /data/todo.db 생성) 후 서버 실행
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
