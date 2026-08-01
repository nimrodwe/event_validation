FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CI=true \
    BIND_HOST=0.0.0.0

COPY docs/requirements.txt docs/requirements.txt
RUN pip install --no-cache-dir -r docs/requirements.txt

COPY . .

EXPOSE 8080 8765

CMD ["python", "run.py", "stack", "--no-open"]
