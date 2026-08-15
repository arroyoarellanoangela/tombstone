FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY sources/ ./sources/
# data/ is not copied — it's bind-mounted at runtime (see docker-compose.yml)
# so a live run's snapshot lands back in the repo, not inside the container.

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
