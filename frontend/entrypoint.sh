#!/bin/sh
set -eu

# See nginx.conf's comment on __HTTPS_PORT_SUFFIX__. Uses a plain sed token
# (not nginx's own $-syntax) specifically so it can never collide with a real
# nginx variable like $host or $request_uri.
sed -i "s/__HTTPS_PORT_SUFFIX__/${HTTPS_PORT_SUFFIX:-}/" /etc/nginx/conf.d/default.conf

exec "$@"
