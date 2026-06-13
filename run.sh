#!/bin/sh
# Build (if needed), start the bankanalyzer web container, and open a browser.
#
# Usage:
#   ./run.sh              # build if missing, run, open in Edge (default)
#   ./run.sh ff           # open in Firefox instead
#   ./run.sh cr           # open in Chrome instead
#   ./run.sh edge         # open in Edge (explicit)
#   ./run.sh --rebuild    # force a rebuild before running
#   ./run.sh --no-browser # start the container only, don't open a browser
#   PORT=8080 ./run.sh    # override host port (default 5000)
#
# Flags and the browser choice can be combined, e.g. ./run.sh --rebuild ff
set -e

IMAGE="bankanalyzer"
CONTAINER="bankanalyzer"
PORT="${PORT:-5000}"
UPLOADS_DIR="${UPLOADS_DIR:-$(pwd)/uploads}"
URL="http://localhost:$PORT"

REBUILD=0
OPEN_BROWSER=1
BROWSER="edge"

# Parse args: browser choice (edge|ff|cr) plus optional flags, in any order.
for arg in "$@"; do
  case "$arg" in
    --rebuild)    REBUILD=1 ;;
    --no-browser) OPEN_BROWSER=0 ;;
    edge|ff|cr)   BROWSER="$arg" ;;
    *) echo "Error: unknown argument '$arg'." >&2; exit 1 ;;
  esac
done

# Pick an available container engine.
if command -v podman >/dev/null 2>&1; then
  ENGINE=podman
elif command -v docker >/dev/null 2>&1; then
  ENGINE=docker
else
  echo "Error: neither podman nor docker found on PATH." >&2
  exit 1
fi

# image_exists: works for both engines (docker has no 'image exists').
image_exists() {
  "$ENGINE" image inspect "$IMAGE" >/dev/null 2>&1
}

# launch the requested browser at $URL. Handles WSL (Windows browsers) and
# native Linux. 'edge'->Edge, 'ff'->Firefox, 'cr'->Chrome.
open_browser() {
  win_edge="/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
  win_chrome="/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
  win_firefox="/mnt/c/Program Files/Mozilla Firefox/firefox.exe"

  is_wsl=0
  case "$(uname -r 2>/dev/null)" in *[Mm]icrosoft*) is_wsl=1 ;; esac

  case "$BROWSER" in
    edge) win_exe="$win_edge";    win_proto="microsoft-edge:$URL"; lin_cmds="microsoft-edge-stable microsoft-edge" ;;
    cr)   win_exe="$win_chrome";  win_proto="";                    lin_cmds="google-chrome-stable google-chrome chromium chromium-browser" ;;
    ff)   win_exe="$win_firefox"; win_proto="";                    lin_cmds="firefox" ;;
  esac

  if [ "$is_wsl" -eq 1 ]; then
    if [ -x "$win_exe" ]; then
      "$win_exe" "$URL" >/dev/null 2>&1 &
      return 0
    fi
    # Fall back to Windows' shell 'start' via cmd.exe.
    if command -v cmd.exe >/dev/null 2>&1; then
      if [ -n "$win_proto" ]; then
        cmd.exe /c start "$win_proto" >/dev/null 2>&1 && return 0
      fi
      cmd.exe /c start "" "$BROWSER" "$URL" >/dev/null 2>&1 && return 0
    fi
  fi

  # Native Linux browsers.
  for c in $lin_cmds; do
    if command -v "$c" >/dev/null 2>&1; then
      "$c" "$URL" >/dev/null 2>&1 &
      return 0
    fi
  done

  echo "Warning: could not locate the '$BROWSER' browser; open $URL manually." >&2
  return 1
}

# wait until the web server answers, up to ~30s.
wait_for_server() {
  i=0
  while [ "$i" -lt 30 ]; do
    if command -v curl >/dev/null 2>&1; then
      curl -sf -o /dev/null "$URL" && return 0
    elif command -v wget >/dev/null 2>&1; then
      wget -q -O /dev/null "$URL" && return 0
    else
      sleep 3; return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  return 1
}

# Build the image if it's missing or a rebuild was requested.
if [ "$REBUILD" -eq 1 ] || ! image_exists; then
  echo "Building image '$IMAGE' with $ENGINE..."
  "$ENGINE" build -t "$IMAGE" -f Containerfile .
fi

# Replace any existing container with the same name.
"$ENGINE" rm -f "$CONTAINER" >/dev/null 2>&1 || true

mkdir -p "$UPLOADS_DIR"

echo "Starting '$CONTAINER' on $URL ..."
"$ENGINE" run -d \
  --name "$CONTAINER" \
  -p "$PORT:5000" \
  -v "$UPLOADS_DIR:/uploads" \
  "$IMAGE" >/dev/null

if [ "$OPEN_BROWSER" -eq 1 ]; then
  echo "Waiting for the server to come up..."
  if wait_for_server; then
    echo "Opening $URL in $BROWSER..."
    open_browser || true
  else
    echo "Warning: server did not respond in time; open $URL manually." >&2
  fi
fi

echo "Container '$CONTAINER' is running. Stop it with: $ENGINE stop $CONTAINER"
echo "Follow logs with: $ENGINE logs -f $CONTAINER"
