# Builder stage
FROM python:3.11-slim as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
        pip install -r requirements.txt

# App stage
FROM python:3.11-slim as app

WORKDIR /app

COPY --from=builder /app /app

ADD app app
ADD run.py run.py
ADD requirements.txt requirements.txt
ADD entrypoint.sh entrypoint.sh

RUN chmod 700 entrypoint.sh
RUN pip install -r requirements.txt

HEALTHCHECK --interval=5s --timeout=3s --retries=3 CMD curl --fail http://localhost:8000/health || exit 1
ENTRYPOINT ["./entrypoint.sh"]
