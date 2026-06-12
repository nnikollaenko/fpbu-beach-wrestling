#!/bin/bash
# ═══════════════════════════════════════════════════════
# ФПБУ Beach Wrestling — One-time Server Setup
# Usage: bash server-setup.sh <domain> <admin_password>
# Example: bash server-setup.sh fpbu-demo.duckdns.org Secure123
# ═══════════════════════════════════════════════════════
set -e

DOMAIN="${1}"
ADMIN_PASSWORD="${2:-fpbu2025}"
APP_DIR="/var/www/beach-wrestling"
SERVICE="beach-wrestling"
REPO="https://github.com/nnikollaenko/fpbu-beach-wrestling.git"
SECRET_KEY=$(openssl rand -hex 32)

if [ -z "$DOMAIN" ]; then
    echo "Usage: bash server-setup.sh <domain> [admin_password]"
    echo "Example: bash server-setup.sh fpbu-demo.duckdns.org Secure123"
    exit 1
fi

echo "🏖️  ФПБУ — Server Setup"
echo "   Domain: $DOMAIN"
echo "   App dir: $APP_DIR"
echo "──────────────────────────────────────────"

# 1. System packages
echo "→ [1/8] Installing system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git curl

# 2. Clone / update repo
echo "→ [2/8] Cloning repository..."
if [ -d "$APP_DIR/.git" ]; then
    echo "   Repo exists — pulling latest..."
    cd "$APP_DIR" && git pull origin main
else
    git clone "$REPO" "$APP_DIR"
fi

# 3. Python venv + deps
echo "→ [3/8] Setting up Python environment..."
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install -q --upgrade pip
"$APP_DIR/venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

# 4. Create uploads dirs
echo "→ [4/8] Creating upload directories..."
mkdir -p "$APP_DIR/static/uploads/athletes"
mkdir -p "$APP_DIR/static/uploads/gallery"
mkdir -p "$APP_DIR/static/uploads/docs"

# 5. Systemd service
echo "→ [5/8] Creating systemd service..."
cat > /etc/systemd/system/${SERVICE}.service << EOF
[Unit]
Description=ФПБУ Beach Wrestling Website
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
Environment="SECRET_KEY=$SECRET_KEY"
Environment="ADMIN_USERS=admin:$ADMIN_PASSWORD"
ExecStart=$APP_DIR/venv/bin/gunicorn -c gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

chown -R www-data:www-data "$APP_DIR"

systemctl daemon-reload
systemctl enable "$SERVICE"
systemctl restart "$SERVICE"
sleep 2
systemctl is-active --quiet "$SERVICE" && echo "   ✅ App service running" || echo "   ❌ App service failed — check: journalctl -u $SERVICE -f"

# 6. Nginx config
echo "→ [6/8] Configuring nginx..."
cat > /etc/nginx/sites-available/$SERVICE << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 20M;

    location /static/ {
        alias $APP_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass         http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header   Host              \$host;
        proxy_set_header   X-Real-IP         \$remote_addr;
        proxy_set_header   X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto \$scheme;
        proxy_read_timeout 60s;
    }

    access_log /var/log/nginx/beach-wrestling.access.log;
    error_log  /var/log/nginx/beach-wrestling.error.log;
}
EOF

ln -sf /etc/nginx/sites-available/$SERVICE /etc/nginx/sites-enabled/$SERVICE
nginx -t
systemctl reload nginx
echo "   ✅ Nginx configured"

# 7. SSL via Let's Encrypt
echo "→ [7/8] Obtaining SSL certificate..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "admin@$DOMAIN" --redirect \
    && echo "   ✅ SSL certificate obtained" \
    || echo "   ⚠️  SSL failed — site works on HTTP. Run manually: certbot --nginx -d $DOMAIN"

# 8. Done
echo ""
echo "══════════════════════════════════════════"
echo "✅ Deploy complete!"
echo ""
echo "   🌐 Site:    https://$DOMAIN"
echo "   🔐 Admin:   https://$DOMAIN/admin"
echo "   👤 Login:   admin / $ADMIN_PASSWORD"
echo ""
echo "   Update site later:"
echo "   cd $APP_DIR && git pull && systemctl restart $SERVICE"
echo "══════════════════════════════════════════"
