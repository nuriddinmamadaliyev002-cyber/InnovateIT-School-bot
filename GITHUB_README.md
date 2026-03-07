# 🎓 InnovateIT School Bot

**Ko'p maktablarni qo'llab-quvvatlovchi zamonaviy maktab boshqaruv Telegram boti**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Telegram Bot API](https://img.shields.io/badge/Telegram%20Bot%20API-21.9-blue.svg)](https://github.com/python-telegram-bot/python-telegram-bot)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 📋 Mundarija

- [Asosiy Imkoniyatlar](#-asosiy-imkoniyatlar)
- [Texnologiyalar](#-texnologiyalar)
- [O'rnatish](#-ornatish)
- [Konfiguratsiya](#-konfiguratsiya)
- [Ishlatish](#-ishlatish)
- [Deployment](#-deployment)
- [Arxitektura](#-arxitektura)
- [Hissa Qo'shish](#-hissa-qoshish)
- [Litsenziya](#-litsenziya)

---

## 🌟 Asosiy Imkoniyatlar

### 👥 Foydalanuvchi Rollari

- **🔐 Super Admin** - butun tizimni boshqaradi
- **👔 Maktab Admin** - o'z maktabini boshqaradi
- **👨‍🏫 O'qituvchi** - darslar, baholar, davomat
- **👨‍🎓 O'quvchi** - topshiriqlar, baholar ko'rish
- **👪 Ota-ona** - farzand ma'lumotlarini ko'rish

### 📚 Asosiy Modullar

#### 1. Davomat Tizimi ✅
- 4 xil status: Keldi, Kelmadi, Kech keldi, Sababli
- O'qituvchi va o'quvchi davomati
- Excel export
- Kun/oy/yil bo'yicha statistika

#### 2. Baho Tizimi 📊
- 3 mezon: Uyga vazifa, Faollik, Intizom
- 1-5 ball tizimi
- Izohlar qo'shish imkoniyati
- O'quvchi/sinf bo'yicha hisobot

#### 3. Topshiriqlar Tizimi 📝
- Dars materiallari yuklash
- Deadline belgilash
- Topshiriqlarni qabul qilish
- Kech topshirish tracking
- Ko'p fayl qo'llab-quvvatlash

#### 4. Maktab Boshqaruvi 🏫
- Ko'p maktab qo'llab-quvvatlash
- Sinflar yaratish va boshqarish
- Fanlar ro'yxati
- O'qituvchi-sinf-fan biriktirish

#### 5. Jadval Tizimi 🗓️
- Haftalik jadval
- Sinf bo'yicha jadval
- PDF/Rasm format qo'llab-quvvatlash

#### 6. Arxiv Tizimi 🗄️
- O'quvchi/o'qituvchilarni arxivlash
- Ma'lumotlarni saqlash
- Qayta faollashtirish

#### 7. Export Tizimi 📤
- Excel (davomat, baholar)
- PDF (hisobotlar)
- Sinf/fan/muddat bo'yicha filter

---

## 🛠️ Texnologiyalar

### Backend
- **Python 3.11+**
- **python-telegram-bot 21.9** - Telegram Bot API
- **SQLite** - Database
- **Repository Pattern** - Clean Architecture

### Kutubxonalar
- `openpyxl` - Excel export
- `reportlab` - PDF generation
- `Pillow` - Rasm ishlash
- `python-dotenv` - Environment variables
- `httpx[socks]` - Proxy qo'llab-quvvatlash

---

## 📥 O'rnatish

### 1. Repository'ni klonlash

```bash
git clone https://github.com/yourusername/InnovateIT_School_bot.git
cd InnovateIT_School_bot
```

### 2. Virtual environment yaratish

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# yoki
venv\Scripts\activate  # Windows
```

### 3. Dependencies o'rnatish

```bash
pip install -r requirements.txt
```

### 4. Environment sozlash

```bash
cp .env.example .env
nano .env  # yoki boshqa editor
```

`.env` faylda sozlash:

```env
BOT_TOKEN=your_bot_token_from_@BotFather
ADMIN_IDS=123456789,987654321
PROXY_URL=  # agar kerak bo'lsa
```

### 5. Botni ishga tushirish

```bash
python bot.py
```

---

## ⚙️ Konfiguratsiya

### Bot Token olish

1. [@BotFather](https://t.me/BotFather) botiga o'ting
2. `/newbot` buyrug'ini yuboring
3. Bot nomi va username'ini kiriting
4. Olingan tokenni `.env` faylga qo'shing

### Admin ID olish

1. [@userinfobot](https://t.me/userinfobot) botiga o'ting
2. Har qanday xabar yuboring
3. Olingan ID raqamini `.env` faylga qo'shing

---

## 🚀 Ishlatish

### Birinchi marta ishga tushirish

1. **Super Admin sifatida kirish**
   - `/start` buyrug'ini yuboring
   - ADMIN_IDS'da bo'lsangiz, super admin paneli ochiladi

2. **Maktab yaratish**
   - "➕ Maktab qo'shish" tugmasini bosing
   - Maktab nomini kiriting

3. **Admin tayinlash**
   - Maktabni tanlang
   - "👔 Admin qo'shish"
   - Admin ma'lumotlarini kiriting

4. **Sinf yaratish**
   - Admin panel orqali sinflar yarating

5. **O'qituvchi qo'shish**
   - O'qituvchi ma'lumotlarini kiriting
   - Sinf va fanlarga biriktiring

6. **O'quvchi qo'shish**
   - O'quvchilarni sinfga biriktiring
   - Telegram ID orqali avtomatik kirish

---

## 🌐 Deployment

### Digital Ocean (tavsiya)

To'liq qo'llanma: [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)

**Tezkor deploy:**

```bash
# 1. Droplet yaratish (Ubuntu 22.04)
# Size: $6/month (1GB RAM)

# 2. SSH orqali ulanish
ssh root@your_droplet_ip

# 3. Deploy script ishlatish
wget https://raw.githubusercontent.com/yourusername/repo/main/deployment/deploy.sh
chmod +x deploy.sh
./deploy.sh

# 4. .env sozlash
nano ~/apps/InnovateIT_School_bot_MULTI_SCHOOL/.env

# 5. Botni ishga tushirish
sudo systemctl start school-bot.service
```

### Boshqa Platformalar

- **VPS** (Ubuntu/Debian)
- **AWS EC2**
- **Google Cloud**
- **Heroku** (kichik loyihalar uchun)

---

## 🏗️ Arxitektura

### Papka Strukturasi

```
InnovateIT_School_bot_MULTI_SCHOOL/
├── bot.py                      # Entry point
├── config.py                   # Konfiguratsiya
├── requirements.txt            # Dependencies
├── .env                        # Environment (git'da yo'q)
│
├── core/                       # Core logic
│   ├── database.py             # Database schema
│   ├── db.py                   # Database connection
│   └── repositories/           # Data access layer
│       ├── user_repo.py        # Foydalanuvchilar
│       ├── class_repo.py       # Sinflar
│       ├── lesson_repo.py      # Darslar
│       ├── grade_repo.py       # Baholar
│       ├── attendance_repo.py  # Davomat
│       └── school_repo.py      # Maktablar
│
├── handlers/                   # Message handlers
│   ├── start.py                # /start command
│   ├── message_router.py       # Text router
│   ├── waiting_router.py       # State management
│   ├── student/                # O'quvchi handlers
│   └── teacher/                # O'qituvchi handlers
│
├── panels/                     # Admin panels
│   ├── super/                  # Super admin
│   └── admin/                  # Maktab admin
│
└── utils/                      # Utilities
    ├── keyboards/              # Keyboard builders
    ├── auth.py                 # Authentication
    ├── attendance_export.py    # Excel export
    └── schedule_export.py      # PDF export
```

### Database Schema

**Asosiy jadvallar:**

- `schools` - Maktablar
- `classes` - Sinflar
- `subjects` - Fanlar
- `teachers` - O'qituvchilar
- `whitelist` - O'quvchilar
- `lessons` - Darslar
- `attendance` - Davomat
- `grades` - Baholar
- `submissions` - Topshiriqlar

**Qo'llab-quvvatlash jadvallari:**

- `teacher_assignments` - O'qituvchi-sinf-fan
- `subject_assignments` - Fan-sinf
- `teacher_weekly_schedule` - Haftalik jadval
- `student_parents` - Ota-ona bog'lanish

---

## 👨‍💻 Development

### Lokal muhitda ishlatish

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate

# Dependencies
pip install -r requirements.txt

# .env sozlash
cp .env.example .env

# Ishga tushirish
python bot.py
```

### Yangi funksiya qo'shish

1. **Handler yaratish**
   ```python
   # handlers/new_feature.py
   async def handle_new_feature(update, context):
       # Kodingiz
   ```

2. **Router'ga qo'shish**
   ```python
   # handlers/message_router.py yoki callbacks_router.py
   from handlers.new_feature import handle_new_feature
   ```

3. **Database migration (agar kerak bo'lsa)**
   ```python
   # core/database.py - _migrate() funksiyasida
   ```

---

## 🧪 Testing

```bash
# Test ishga tushirish (agar mavjud bo'lsa)
pytest tests/

# Coverage
pytest --cov=.
```

---

## 🤝 Hissa Qo'shish

Hissa qo'shmoqchi bo'lsangiz:

1. **Fork** qiling
2. **Branch** yarating (`git checkout -b feature/amazing-feature`)
3. **Commit** qiling (`git commit -m 'Add amazing feature'`)
4. **Push** qiling (`git push origin feature/amazing-feature`)
5. **Pull Request** oching

### Kod Standartlari

- PEP 8 stylega rioya qiling
- Docstring'lar yozing
- Type hints ishlatish tavsiya etiladi
- Commit xabarlari aniq bo'lsin

---

## 📝 Changelog

### Version 2.0 (2024-03)
- ✅ Ko'p maktab qo'llab-quvvatlash
- ✅ Arxiv tizimi
- ✅ Ota-ona funksiyasi
- ✅ Lesson deadline
- ✅ Izohlar tizimi

### Version 1.0 (2023-12)
- ✅ Asosiy funksiyalar
- ✅ Davomat tizimi
- ✅ Baho tizimi
- ✅ Topshiriqlar

---

## 📄 Litsenziya

MIT License - batafsil [LICENSE](LICENSE) faylida

---

## 🙏 Minnatdorchilik

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Ajoyib kutubxona
- [Digital Ocean](https://www.digitalocean.com/) - Hosting
- Barcha foydalanuvchilar va kontributorlar

---

## 📞 Aloqa

**Muallif:** InnovateIT Team

**Savol va takliflar:**
- Telegram: [@your_username](https://t.me/your_username)
- Email: your-email@example.com
- Issues: [GitHub Issues](https://github.com/yourusername/repo/issues)

---

## 🌟 Qo'llab-quvvatlash

Agar loyiha yoqsa, **⭐ Star** bosishni unutmang!

---

<div align="center">
  <strong>Made with ❤️ in Uzbekistan 🇺🇿</strong>
</div>
