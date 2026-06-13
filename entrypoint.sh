#!/bin/sh
set -e

# Ensure UPLOAD_DIR exists and attempt to set ownership to the appuser created in the image.
if [ -n "$UPLOAD_DIR" ]; then
  mkdir -p "$UPLOAD_DIR"
  chown -R appuser:appuser "$UPLOAD_DIR" 2>/dev/null || true
fi

exec "$@"
