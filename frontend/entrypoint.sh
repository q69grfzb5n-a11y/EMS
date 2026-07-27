#!/bin/sh
set -eu

# See nginx.conf's comment on __HTTPS_PORT_SUFFIX__. Uses a plain sed token
# (not nginx's own $-syntax) specifically so it can never collide with a real
# nginx variable like $host or $request_uri.
sed -i "s/__HTTPS_PORT_SUFFIX__/${HTTPS_PORT_SUFFIX:-}/" /etc/nginx/conf.d/default.conf

# HSTS is keyed on the HOSTNAME and ignores the port, so sending it from a
# local/test deployment poisons plain-HTTP access to *every* port on that
# hostname — including this stack's own HTTP->HTTPS redirect listener, and any
# other dev server the developer runs on localhost. The browser rewrites
# http://localhost:<port> to https:// before the request is ever sent, so the
# redirect can never run and the failure looks like a server bug.
# Only emit it when explicitly enabled (real domain + real certificate).
if [ "${ENABLE_HSTS:-0}" = "1" ]; then
    sed -i "s|__HSTS_HEADER__|add_header Strict-Transport-Security \"max-age=63072000; includeSubDomains\" always;|g" \
        /etc/nginx/conf.d/default.conf
else
    sed -i "s|__HSTS_HEADER__||g" /etc/nginx/conf.d/default.conf
fi

# Self-provision a TLS certificate when none is present.
#
# certs/ is gitignored (it holds private keys), so a fresh clone has none. This
# used to mean nginx died on startup with a raw OpenSSL "cannot load
# certificate" error and sat in a restart loop — the site simply never came up,
# and the only clue was buried in `docker logs`. Requiring a manual script run
# before the very first `docker compose up` was a poor default: nothing
# enforced it, and skipping it failed obscurely.
#
# A real deployment bind-mounts real certificates over this path, in which case
# the files already exist and this block does nothing.
CERT_DIR=/etc/nginx/certs
if [ ! -f "$CERT_DIR/localhost.crt" ] || [ ! -f "$CERT_DIR/localhost.key" ]; then
    echo "No TLS certificate found in $CERT_DIR — generating a self-signed one."
    echo "Replace it with a real certificate for any non-local deployment."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
        -keyout "$CERT_DIR/localhost.key" \
        -out "$CERT_DIR/localhost.crt" \
        -subj "/CN=localhost" \
        -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null
    echo "Self-signed certificate generated (valid 365 days, CN=localhost)."
fi

exec "$@"
