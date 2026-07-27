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

exec "$@"
