FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /bin/uv

# UV_NO_CACHE: the download cache would otherwise be baked into the layer next to the installed copy.
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first so code changes don't reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project
COPY plumbline ./plumbline
RUN uv sync --frozen --no-dev

# uagents-core opens uagents_core.log in the working directory on import, so the app user must
# be able to write there (without it the checker crashes at startup).
RUN useradd --create-home app && chown app /app
USER app
EXPOSE 8000
CMD ["sh", "-c", "uvicorn plumbline.api:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
