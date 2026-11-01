#!/bin/sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

# Run as root: this writes system-wide service files on the EC2 host.
cat > /etc/systemd/system/zai-cert-renew.service <<EOF
[Unit]
Description=Renew the ZAI HTTPS certificate and reload Caddy
Requires=docker.service
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$project_dir
ExecStart=/usr/bin/make prod-cert-renew
EOF

cat > /etc/systemd/system/zai-cert-renew.timer <<'EOF'
[Unit]
Description=Check the ZAI HTTPS certificate twice a day

[Timer]
OnCalendar=*-*-* 00,12:00:00
RandomizedDelaySec=30m
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now zai-cert-renew.timer
systemctl list-timers zai-cert-renew.timer
