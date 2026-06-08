#!/bin/bash
# ═══════════════════════════════════════════
# ФПБУ — Deploy script for Ubuntu/Debian VPS
# Usage: bash deploy.sh
# ═══════════════════════════════════════════
set -e

APP_DIR="/var/www/beach-wrestling"
SERVICE="beach-wrestling"
DOMAIN="yourdomain.com"   # ← замінити на реальний домен

echo "🏖️  ФПБУ Website — Deploy"
echo "──────────────────────────"

# 1. System deps
echo "→ Installing system packages..."
apt-get update -qq
apt-get install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# 2. Create app directory
mkdir -p $APP_DIR
mkdir -p /var/log/beach-wrestling

# 3. Copy files (run from project root)
echo "→ Copying project files..."
rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='data/wrestling.db' \
    . $APP_DIR/

# 4. Python venv + dependencies
echo "→ Setting up Python virtualenv..."
python3 -m venv $APP_DIR/venv
$APP_DIR/venv/bin/pip install -q --upgrade pip
$APP_DIR/venv/bin/pip install -q -r $APP_DIR/requirements.txt

# 5. Init DB
echo "→ Initializing database..."
cd $APP_DIR && venv/bin/python -c "import db; db.init_db(); print('Database OK')"

# 6. Systemd service
echo "→ Creating systemd service..."
cat > /etc/systemd/system/${SERVICE}.service << EOF
[Unit]
Description=ФПБУ Beach Wrestling Website
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/venv/bin/gunicorn -c gunicorn.conf.py app:app
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

chown -R www-data:www-data $APP_DIR /var/log/beach-wrestling

systemctl daemon-reload
systemctl enable $SERVICE
systemctl restart $SERVICE

# 7. Nginx
echo "→ Configuring nginx..."
sed "s/yourdomain.com/$DOMAIN/g" $APP_DIR/nginx.conf > /etc/nginx/sites-available/$SERVICE
ln -sf /etc/nginx/sites-available/$SERVICE /etc/nginx/sites-enabled/$SERVICE
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

# 8. SSL
echo "→ Obtaining SSL certificate..."
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN || \
    echo "SSL: configure manually with: certbot --nginx -d $DOMAIN"

echo ""
echo "✅ Deploy complete!"
echo "   Site: https://$DOMAIN"
echo "   Logs: journalctl -u $SERVICE -f"
