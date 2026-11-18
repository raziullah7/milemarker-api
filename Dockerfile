# The API's images, built in stages (NFR-25):
#
#   runtime   what runs: the virtual environment, the code and the data. The default target.
#   test      the runtime's code with the test tools, the tests and the recorded roads; it
#             runs the suite, and the stand-in routing server of the end-to-end stack.
#
# Base images are pinned by digest, so a rebuild is the image that was tested; Dependabot
# proposes new digests (Q0a-21).

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS base

# No buffering, so log lines appear at once.
ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

# The user the processes run as. It owns nothing under /app, so it cannot change the code or
# the data. It can still write to /tmp and to its home directory, which gunicorn 27 needs
# for its control socket.
RUN useradd --system --create-home app
WORKDIR /app


# The virtual environment, built with uv, which stays in this stage.
FROM base AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.19@sha256:b46b03ddfcfbf8f547af7e9eaefdf8a39c8cebcba7c98858d3162bd28cf536f6 /uv /bin/uv

# Bytecode compiled at build time makes the first start faster. Copy (not hard-link) because
# the cache mount and the venv are on different filesystems.
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Dependencies alone: this layer is rebuilt only when pyproject.toml or uv.lock change. The
# project is not a package (no build system), so there is nothing more to install.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev


# The test tools added to the same environment, then everything the build may see.
FROM build AS test

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project

COPY . /app

USER app
# The code is read-only for the app user, so pytest cannot keep its cache there.
CMD ["pytest", "-p", "no:cacheprovider"]


# Only what runs: no uv, no tests, no recordings, no documents.
FROM base AS runtime

COPY --from=build /app/.venv /app/.venv
COPY manage.py gunicorn.conf.py /app/
COPY config /app/config
COPY stations /app/stations
COPY trips /app/trips
COPY data /app/data

USER app
EXPOSE 8000
CMD ["gunicorn", "--config", "gunicorn.conf.py"]
