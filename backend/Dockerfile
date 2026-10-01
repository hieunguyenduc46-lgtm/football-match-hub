# Backend image (FastAPI). Used by the Jenkins Deploy/Release stages and any Docker host.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Apply the latest Debian security patches available for the base image.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Supply-chain hardening (SonarCloud docker:S8541 / S8544):
#  - requirements.lock pins EVERY package (including dependencies) with SHA-256 hashes,
#  - --only-binary :all: installs pre-built wheels only, so no setup.py scripts are executed.
# pip is then removed: the running container does not need a package manager
# (this also removes pip's bundled libraries that Trivy reported in build #4).
COPY requirements.lock .
RUN pip install --no-cache-dir --only-binary :all: --require-hashes -r requirements.lock \
    && python -m pip uninstall -y pip

# Copy only the application code (not the whole folder) - SonarCloud docker:S6470.
COPY *.py ./
COPY routers/ ./routers/

# Least privilege: run as a non-root user so a compromised app cannot change the system.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# Docker marks the container "unhealthy" if /api/health stops answering.
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/health' % os.environ.get('PORT', '8000'), timeout=4)" || exit 1

# Host must be 0.0.0.0; the port comes from the PORT environment variable (default 8000).
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
