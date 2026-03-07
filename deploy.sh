#!/bin/bash
# ══════════════════════════════════════════════════════════
# Digital Ocean Droplet — Avtomatik o'rnatish skripti
# Ubuntu 22.04 uchun
# Ishlatish: bash deploy.sh
# ══════════════════════════════════════════════════════════

set -e  # Xato bo'lsa to'xta

echo "🚀 Bot o'rnatish boshlandi..."

# ── 1. Tizim yangilash ──────────────────────────────────────
echo "📦 Tizim yangilanmoqda..."
apt update && apt upgrade -y

# ── 2. Kerakli paketlar ─────────────────────────────────────
echo "📦 Paketlar o'rnatilmoqda..."
apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib git

# ── 3. PostgreSQL sozlash ───────────────────────────────────
echo "🗄️ PostgreSQL sozlanmoqda..."
systemctl start postgresql
systemctl enable postgresql

# DB va foydalanuvchi yaratish
sudo -u postgres psql << 'SQLEOF'
CREATE DATABASE schoolbot_db;
CREATE USER schoolbot_user WITH PASSWORD 'O_ZINGIZNING_PAROLINGIZ';
GRANT ALL PRIVILEGES ON DATABASE schoolbot_db TO schoolbot_user;
ALTER DATABASE schoolbot_db OWNER TO schoolbot_user;
\q
SQLEOF

echo "✅ PostgreSQL tayyor!"

# ── 4. Loyihani klonlash ────────────────────────────────────
echo "📥 Kod yuklanmoqda..."
cd /home/ubuntu
git clone https://github.com/nuriddinmamadaliyev002-cyber/InnovateIT-School-bot.git bot
cd bot

# ── 5. Virtual muhit va paketlar ────────────────────────────
echo "🐍 Python muhiti sozlanmoqda..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# ── 6. .env fayl ────────────────────────────────────────────
echo "⚙️ .env fayl yarating:"
echo "nano /home/ubuntu/bot/.env"

# ── 7. Systemd service ──────────────────────────────────────
cat > /etc/systemd/system/schoolbot.service << 'SVCEOF'
[Unit]
Description=InnovateIT School Bot
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/bot
ExecStart=/home/ubuntu/bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
EnvironmentFile=/home/ubuntu/bot/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload
systemctl enable schoolbot

echo ""
echo "════════════════════════════════════════"
echo "✅ O'rnatish tugadi!"
echo ""
echo "Keyingi qadamlar:"
echo "1. nano /home/ubuntu/bot/.env  → .env ni to'ldiring"
echo "2. systemctl start schoolbot   → Botni ishga tushiring"
echo "3. systemctl status schoolbot  → Holatini tekshiring"
echo "4. journalctl -u schoolbot -f  → Loglarni ko'ring"
echo "════════════════════════════════════════"
