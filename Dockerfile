FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY ./src ./src
COPY ./static ./static
COPY ./frontend_dist ./frontend_dist

ENV PYTHONPATH=/app/src

CMD ["sh", "-c", "python src/init_db.py && uvicorn main:app --host 0.0.0.0 --port 8000"]