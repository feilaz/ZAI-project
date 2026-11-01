#!/bin/sh
set -eu

if [ "${1:-}" = "issue" ]; then
    exec certbot certonly \
        --non-interactive \
        --agree-tos \
        --email "$ACME_EMAIL" \
        --server https://acme-v02.api.letsencrypt.org/directory \
        --preferred-profile shortlived \
        --webroot --webroot-path /var/www/certbot \
        --cert-name zai \
        --ip-address "$PUBLIC_IP" \
        --keep-until-expiring
fi

exec certbot "$@"
