# Allow selecting a base image for RHEL9 compatibility (pass `--build-arg BASE_IMAGE=...`).
ARG BASE_IMAGE=python:3.11-slim
FROM ${BASE_IMAGE}

ENV PYTHONUNBUFFERED=1
# Default uploads directory inside the container (can be overridden at runtime)
ENV UPLOAD_DIR=/uploads

WORKDIR /app

# NOTE: intentionally not installing OS packages here because some rootless
# builders (crun/podman) can fail when package managers trigger systemd/dbus
# calls. Choose a `BASE_IMAGE` that already includes `ca-certificates`, or
# install OS packages manually in your build environment. Examples:
#  - Use Debian/Ubuntu-based image: `python:3.11-slim` (often has CA certs)
#  - Use Red Hat UBI Python image: pass `--build-arg BASE_IMAGE=registry.redhat.io/ubi9/python-39:latest`
# If your target base lacks `ca-certificates`, install them in a separate
# build step on a builder that permits package-manager operations.#
# The image intentionally has no HEALTHCHECK because Podman rootless/crun can
# fail to create systemd healthcheck timers when no user systemd session is
# available. External health checks should be managed by the runtime or CI.
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . /app

# Add an entrypoint that ensures the upload directory exists
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Create a non-root user for running the app and ensure upload dir exists
RUN groupadd -g 1000 appuser || true \
 && useradd -m -u 1000 -g appuser appuser || true \
 && mkdir -p "$UPLOAD_DIR" \
 && chown -R appuser:appuser "$UPLOAD_DIR" || true

EXPOSE 5000

# Note: HEALTHCHECK removed to improve rootless Podman/crun compatibility.
# Rootful runs can still perform external health checks via the host or CI.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["gunicorn", "web_app:app", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120"]
