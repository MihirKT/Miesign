#!/usr/bin/env bash
# One-shot provisioning for the Miesign e2-micro VM (Debian 12): gunicorn behind Caddy, frontend served by Caddy.
# Usage (on the VM, after copying miesign.tgz, dist.tgz and settings.py to /tmp): sudo bash setup.sh <host>
#
# Miesign · Author: Mihir Kapildev Tiwari
set -euo pipefail
HOST="$1"
APP=/opt/miesign

# 1 GB RAM is tight for pip installs and two workers; swap keeps the box from OOM-killing gunicorn.
if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

apt-get update -q && apt-get install -yq python3-venv caddy
id miesign >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin miesign

mkdir -p "$APP/web"
tar -xzf /tmp/miesign.tgz -C "$APP"
cp /tmp/settings.py "$APP/backend/config/settings.py"
rm -rf "$APP/web/dist" && tar -xzf /tmp/dist.tgz -C "$APP/web"

[ -d "$APP/venv" ] || python3 -m venv "$APP/venv"
"$APP/venv/bin/pip" install -q -r "$APP/backend/requirements.txt"

if [ ! -f "$APP/env" ]; then
  cat > "$APP/env" <<EOF
DJANGO_SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=$HOST
EOF
  chmod 600 "$APP/env"
fi

chown -R miesign:miesign "$APP"
sudo -u miesign bash -c "set -a; . $APP/env; cd $APP/backend && $APP/venv/bin/python manage.py migrate --noinput"

# Renders take 20-40 s, so the worker timeout is well above gunicorn's 30 s default.
# Requests mostly wait on Gemini, so threads (cheap on 1 GB) let 8 users be served at once instead of 2.
cat > /etc/systemd/system/miesign.service <<EOF
[Unit]
Description=Miesign API (gunicorn)
After=network.target

[Service]
User=miesign
WorkingDirectory=$APP/backend
EnvironmentFile=$APP/env
ExecStart=$APP/venv/bin/gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --threads 4 --timeout 180
Restart=always

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/caddy/Caddyfile <<EOF
$HOST {
	encode gzip
	request_body {
		max_size 16MB
	}
	@backend path /api/* /media/*
	handle @backend {
		reverse_proxy 127.0.0.1:8000
	}
	handle {
		root * $APP/web/dist
		try_files {path} /index.html
		file_server
	}
}
EOF

systemctl daemon-reload
systemctl enable --now miesign
systemctl restart miesign caddy
systemctl --no-pager --lines 0 status miesign caddy
