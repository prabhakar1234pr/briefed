FROM python:3.12-slim-bookworm

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
  fastapi \
  "uvicorn[standard]" \
  httpx \
  PyJWT \
  cryptography \
  supabase \
  "google-cloud-aiplatform>=1.60.0" \
  "google-cloud-texttospeech>=2.16.0" \
  vertexai \
  "google-genai>=1.0.0"

COPY app ./app

ENV PORT=8080
EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
