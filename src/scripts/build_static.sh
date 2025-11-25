#!/usr/bin/env bash
set -eu

# Resolve directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/../backend" && pwd)"
FRONTEND_DIR="$(cd "${SCRIPT_DIR}/../frontend" && pwd)"
DEST_DIR="${BACKEND_DIR}/static"
SRC_DIR="${FRONTEND_DIR}/static"

echo "Building frontend in ${FRONTEND_DIR}..."
if command -v yarn >/dev/null 2>&1; then
  yarn --cwd "${FRONTEND_DIR}" install --frozen-lockfile
  yarn --cwd "${FRONTEND_DIR}" build
else
  npm --prefix "${FRONTEND_DIR}" ci --silent --no-audit --no-fund || npm --prefix "${FRONTEND_DIR}" install --silent --no-audit --no-fund
  npm --prefix "${FRONTEND_DIR}" run build
fi

if [[ ! -d "${SRC_DIR}" ]]; then
  echo "Error: build output not found at ${SRC_DIR}"
  exit 1
fi

echo "Copying assets from ${SRC_DIR} to ${DEST_DIR}..."
rm -rf "${DEST_DIR}"
mkdir -p "${DEST_DIR}"
if command -v rsync >/dev/null 2>&1; then
  rsync -a --delete "${SRC_DIR}/" "${DEST_DIR}/"
else
  cp -R "${SRC_DIR}/." "${DEST_DIR}/"
fi

echo "Static assets copied to ${DEST_DIR}"


