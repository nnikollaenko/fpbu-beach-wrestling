#!/bin/bash
# ═══════════════════════════════════════════════════════
# ФПБУ Beach Wrestling — Update script (run after git push)
# Usage: bash server-update.sh
# ═══════════════════════════════════════════════════════
set -e

APP_DIR="/var/www/beach-wrestling"
SERVICE="beach-wrestling"

echo "🔄 Updating ФПБУ website..."

cd "$APP_DIR"
git pull origin main
"$APP_DIR/venv/bin/pip" install -q -r requirements.txt
chown -R www-data:www-data "$APP_DIR"
systemctl restart "$SERVICE"
sleep 1
systemctl is-active --quiet "$SERVICE" && echo "✅ Done — site updated" || echo "❌ Service failed — check: journalctl -u $SERVICE -f"
