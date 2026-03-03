FROM python:3.9-slim

ENV USERNAME=appuser
ENV USER_UID=10453
ENV USER_GID=$USER_UID

RUN groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME}

WORKDIR /app

COPY uv.lock pyproject.toml .
RUN pip install uv --no-cache-dir \
    && uv sync --no-cache-dir

COPY . .
RUN chown -R ${USERNAME}:${USERNAME} /app

USER ${USERNAME}

EXPOSE 8080
CMD ["uv","run", "src/app.py"]
