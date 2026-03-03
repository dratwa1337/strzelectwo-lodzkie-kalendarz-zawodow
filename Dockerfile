FROM python:3.9-slim

ARG USER_UID=10453
ARG USER_GID=${USER_UID}

RUN groupadd --gid ${USER_GID} appuser && \
    useradd --uid ${USER_UID} --gid ${USER_GID} --no-log-init -m appuser

WORKDIR /app

# Install uv
RUN pip install uv --no-cache-dir

# Install dependencies first (cached layer)
COPY --chown=appuser:appuser uv.lock pyproject.toml ./
RUN uv sync --frozen --no-cache

# Copy application code
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser data/ ./data/

USER appuser

EXPOSE 8080
CMD ["uv", "run", "--no-sync", "python", "src/app.py"]
