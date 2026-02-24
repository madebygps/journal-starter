# ============================================
# Stage 1: Build — install dependencies with uv
# ============================================
FROM python:3.12-slim AS builder

# Install uv (fast Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for Docker layer caching
COPY pyproject.toml uv.lock ./

# Install production dependencies into a virtual environment
RUN uv sync --frozen --no-dev --no-install-project

# ============================================
# Stage 2: Runtime — lean production image
# ============================================
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Make sure the virtualenv binaries are on the PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Copy application code
COPY api/ ./api/
COPY database_setup.sql ./database_setup.sql

# Expose the application port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
