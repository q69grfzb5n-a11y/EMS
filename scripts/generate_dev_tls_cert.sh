#!/usr/bin/env bash
set -euo pipefail

# Generates a self-signed TLS cert/key for LOCAL testing of the prod Docker
# Compose profile only. A real deployment must replace certs/localhost.{crt,key}
# with a real certificate (e.g. Let's Encrypt) at the same path — nginx.conf
# doesn't change either way, only the files it points at.
#
# Requires openssl (bundled with Git for Windows / present on Linux/macOS).
# Usage: scripts/generate_dev_tls_cert.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERTS_DIR="$ROOT_DIR/certs"
mkdir -p "$CERTS_DIR"

if [ -f "$CERTS_DIR/localhost.crt" ] && [ -f "$CERTS_DIR/localhost.key" ]; then
  echo "Certs already exist at $CERTS_DIR — delete them first if you want to regenerate."
  exit 0
fi

# cd into the target dir and use relative filenames + MSYS_NO_PATHCONV: Git
# Bash's path-conversion otherwise mangles the leading-slash "/CN=..." subject
# and absolute -keyout/-out paths on Windows.
(
  cd "$CERTS_DIR"
  MSYS_NO_PATHCONV=1 openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout localhost.key \
    -out localhost.crt \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"
)

echo "OK: self-signed cert written to $CERTS_DIR (valid 365 days, CN=localhost)."
echo "Browsers will warn this cert isn't trusted — expected for local testing;"
echo "click through the warning, or import localhost.crt into your OS/browser trust store."
