# 🚀 GitHub'ga Joylashtirish Qo'llanmasi

## 📋 Bosqichma-bosqich yo'riqnoma

### 1️⃣ GitHub'da yangi repository yaratish

1. [GitHub](https://github.com) ga kiring
2. **New repository** tugmasini bosing
3. Repository sozlamalari:
   - **Name**: `InnovateIT-School-Bot`
   - **Description**: "Ko'p maktablarni qo'llab-quvvatlovchi Telegram bot"
   - **Visibility**: 
     - ✅ **Private** (maxfiy bo'lishi uchun - TAVSIYA)
     - ⚠️ **Public** (ochiq manba bo'lishi uchun)
   - **⚠️ MUHIM**: 
     - "Add a README file" - **BELGILAMANG** ❌
     - "Add .gitignore" - **BELGILAMANG** ❌
     - "Choose a license" - **BELGILAMANG** ❌
4. **Create repository** tugmasini bosing

---

### 2️⃣ Lokal kompyuterda Git sozlash

#### A) Git o'rnatish (agar yo'q bo'lsa)

**Windows:**
```bash
# Git yuklab olish: https://git-scm.com/downloads
# O'rnatgandan keyin Git Bash ni oching
```

**Linux/Mac:**
```bash
# Ubuntu/Debian
sudo apt install git

# Mac (Homebrew)
brew install git
```

#### B) Git konfiguratsiya

```bash
git config --global user.name "Sizning Ismingiz"
git config --global user.email "sizning-email@example.com"
```

---

### 3️⃣ Loyihani Git'ga qo'shish

#### A) Loyiha papkasiga o'tish

```bash
cd /path/to/InnovateIT_School_bot_MULTI_SCHOOL
```

#### B) Zaruriy fayllarni ko'chirish

```bash
# .gitignore faylni ko'chirish
cp /path/to/downloaded/.gitignore .

# .env.example faylni ko'chirish
cp /path/to/downloaded/.env.example .

# README.md faylni ko'chirish (GITHUB_README.md → README.md)
cp /path/to/downloaded/GITHUB_README.md README.md
```

#### C) Git repository yaratish

```bash
# Git init
git init

# Barcha fayllarni qo'shish
git add .

# Birinchi commit
git commit -m "Initial commit: InnovateIT School Bot v1.0"
```

---

### 4️⃣ GitHub'ga yuklash

#### A) Remote repository qo'shish

```bash
# GitHub repository URL'ini qo'shish
git remote add origin https://github.com/YOUR_USERNAME/InnovateIT-School-Bot.git

# Tekshirish
git remote -v
```

#### B) GitHub'ga push qilish

```bash
# Main branchni push qilish
git branch -M main
git push -u origin main
```

**⚠️ Agar parol so'ralsa:**

GitHub 2021-yildan boshlab password authentication ishlamaydi!

**Personal Access Token (PAT) yaratish:**

1. GitHub → **Settings** → **Developer settings**
2. **Personal access tokens** → **Tokens (classic)**
3. **Generate new token (classic)**
4. Sozlamalar:
   - **Note**: "Bot Deployment"
   - **Expiration**: 90 days (yoki No expiration)
   - **Scopes**: `repo` ni belgilang ✅
5. **Generate token** → Tokenni **nusxalab oling** (qayta ko'rsatilmaydi!)

**Push qilishda:**
```bash
Username: YOUR_GITHUB_USERNAME
Password: ghp_xxxxxxxxxxxxxxxxxxxx  # PAT'ni kiriting
```

---

### 5️⃣ Deployment fayllarini qo'shish

#### A) Deployment papka yaratish

```bash
mkdir deployment
```

#### B) Deployment fayllarni ko'chirish

```bash
# Deploy scriptlar
cp /path/to/downloaded/deploy.sh deployment/
cp /path/to/downloaded/backup.sh deployment/
cp /path/to/downloaded/monitor.sh deployment/
cp /path/to/downloaded/DEPLOYMENT_GUIDE.md deployment/
cp /path/to/downloaded/README.md deployment/

# Executable qilish
chmod +x deployment/*.sh
```

#### C) Commit va push

```bash
git add deployment/
git commit -m "Add deployment scripts and documentation"
git push
```

---

### 6️⃣ GitHub Actions sozlash (ixtiyoriy)

```bash
# .github/workflows papka yaratish
mkdir -p .github/workflows

# Workflow faylni ko'chirish
cp /path/to/downloaded/.github_workflows_test.yml .github/workflows/test.yml

# Commit va push
git add .github/
git commit -m "Add GitHub Actions workflow"
git push
```

---

### 7️⃣ README.md ni tahrirlash

```bash
# README.md ni ochish
nano README.md  # yoki code README.md

# Quyidagilarni o'zgartiring:
# - YOUR_USERNAME → haqiqiy GitHub username
# - your-email@example.com → haqiqiy email
# - Telegram username
```

**Commit va push:**

```bash
git add README.md
git commit -m "Update README with correct information"
git push
```

---

## ✅ Tekshirish

GitHub repository'ingizga o'ting:
```
https://github.com/YOUR_USERNAME/InnovateIT-School-Bot
```

**Ko'rinishi kerak:**
```
✅ README.md (to'liq ma'lumot)
✅ .gitignore (maxfiy fayllar yo'q)
✅ .env.example (namuna)
✅ requirements.txt
✅ bot.py, config.py, va boshqalar
✅ deployment/ papka
❌ .env fayl YO'Q (maxfiy!)
❌ school.db fayl YO'Q (database yo'q!)
❌ __pycache__/ papka YO'Q
```

---

## 🔐 Xavfsizlik Checklist

Quyidagilar **GitHub'da BO'LMASLIGI kerak:**

- ❌ `.env` fayl (BOT_TOKEN, ADMIN_IDS)
- ❌ `school.db` (database)
- ❌ `*.log` fayllar
- ❌ `backups/` papka
- ❌ `__pycache__/` papka
- ❌ Shaxsiy ma'lumotlar

**Agar yuklangan bo'lsa:**

```bash
# Faylni Git'dan o'chirish (lekin lokal kompyuterda qoldirish)
git rm --cached .env
git rm --cached school.db

# Commit va push
git commit -m "Remove sensitive files"
git push

# .gitignore'ga qo'shish
echo ".env" >> .gitignore
echo "*.db" >> .gitignore
git add .gitignore
git commit -m "Update .gitignore"
git push
```

---

## 🌿 Branch Strategiya (ilg'or)

### Main branch (production)
```bash
git checkout main
```

### Development branch
```bash
# Yangi branch yaratish
git checkout -b develop

# O'zgarishlar qilish
# ...

# Commit
git add .
git commit -m "Add new feature"

# Push
git push -u origin develop
```

### Feature branch
```bash
# Feature branch yaratish
git checkout -b feature/attendance-export

# Ishlab chiqish
# ...

# Commit va push
git add .
git commit -m "Implement attendance export to Excel"
git push -u origin feature/attendance-export
```

**Pull Request qilish:**
1. GitHub'da **Pull requests** → **New pull request**
2. `feature/attendance-export` → `develop`
3. **Create pull request**
4. Review va merge

---

## 🔄 Yangilanishlarni push qilish

```bash
# O'zgarishlarni ko'rish
git status

# Barcha o'zgarishlarni qo'shish
git add .

# Yoki faqat ma'lum fayllar
git add bot.py config.py

# Commit
git commit -m "Fix: attendance export bug"

# Push
git push
```

---

## 📥 Serverda yangilash

```bash
# Serverga SSH orqali ulanish
ssh user@your_server_ip

# Loyiha papkasiga o'tish
cd ~/apps/InnovateIT_School_bot_MULTI_SCHOOL

# Yangi kodni olish
git pull origin main

# Dependencies yangilash (agar kerak bo'lsa)
source venv/bin/activate
pip install -r requirements.txt

# Botni qayta ishga tushirish
sudo systemctl restart school-bot.service

# Statusni tekshirish
sudo systemctl status school-bot.service
```

---

## 🆘 Muammolarni Hal Qilish

### "fatal: remote origin already exists"

```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/repo.git
```

### "Permission denied (publickey)"

```bash
# HTTPS ishlatish (PAT bilan)
git remote set-url origin https://github.com/YOUR_USERNAME/repo.git

# Yoki SSH kalit sozlash
ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
# Public kalitni GitHub'ga qo'shish
```

### ".env fayl tasodifan yuklangan"

```bash
# Git'dan o'chirish
git rm --cached .env
git commit -m "Remove .env file"
git push

# GitHub'da ham commit history'dan o'chirish kerak bo'lsa:
# BFG Repo-Cleaner yoki git filter-branch ishlatish
```

---

## 📚 Foydali Git Komandalar

```bash
# Holatni ko'rish
git status

# O'zgarishlarni ko'rish
git diff

# Commit history
git log --oneline

# Branch'lar ro'yxati
git branch

# Remote repository'lar
git remote -v

# Oxirgi commit'ni bekor qilish
git reset --soft HEAD~1

# Hamma o'zgarishlarni bekor qilish (EHTIYOT!)
git reset --hard HEAD
```

---

## ✅ To'liq Checklist

- [ ] GitHub repository yaratildi
- [ ] `.gitignore` fayl qo'shildi
- [ ] `.env.example` fayl qo'shildi
- [ ] `README.md` to'ldirildi
- [ ] Deployment fayllar qo'shildi
- [ ] Maxfiy ma'lumotlar Git'da yo'q
- [ ] Birinchi commit qilindi
- [ ] GitHub'ga push qilindi
- [ ] Repository xavfsiz (private)
- [ ] GitHub Actions sozlandi (ixtiyoriy)

---

**Tayyor! GitHub'da professional repository tayyorsiz! 🎉**

Keyingi qadamlar: [DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md)
