FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg curl ca-certificates gnupg git \
    && rm -rf /var/lib/apt/lists/*

# Node + Claude Code CLI (usado apenas pelo worker)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g @anthropic-ai/claude-code

WORKDIR /app
COPY pyproject.toml ./
RUN pip install -e .[dev]

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
