FROM python:3.15-slim

# A pinned uv, so the build does not change when uv does. Only the binary is copied.
COPY --from=ghcr.io/astral-sh/uv:0.11.19 /uv /bin/uv

# Bytecode compiled at build time makes the first start faster. Copy (not hard-link) because
# the cache mount and the venv are on different filesystems. No buffering, so logs appear at once.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# "0" for the API image; "1" adds pytest and ruff for the test image. The only difference.
ARG WITH_TEST_TOOLS=0

# A user that cannot write to the code or install anything if the process is compromised.
# It needs a home directory: gunicorn 27 puts its control socket in ~/.gunicorn and logs an
# error at start-up without one.
RUN useradd --system --create-home app
WORKDIR /app

# Dependencies first and alone: this layer is rebuilt only when pyproject.toml or uv.lock change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ "$WITH_TEST_TOOLS" = "1" ]; then GROUPS_FLAG="--group dev"; else GROUPS_FLAG="--no-dev"; fi; \
    uv sync --frozen --no-install-project $GROUPS_FLAG

# The project's own code, after the dependencies. The project is not a package (no build
# system), so there is nothing more to install.
COPY . /app

USER app
EXPOSE 8000
CMD ["sh", "docker/entrypoint.sh"]
