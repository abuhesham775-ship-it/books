# Smart Books Library Bot 📚

بوت تيليجرام متكامل لإدارة مكتبة رقمية مع لوحة تحكم للمالك.

## الميزات الرئيسية

- 📚 إدارة الكتب والمؤلفين والأقسام
- 🔍 بحث متقدم ونصّي وذكي بالذكاء الاصطناعي
- ⭐ نظام التقييمات والمراجعات
- 🎁 نظام النقاط والمكافآت
- 👥 إدارة المستخدمين (حظر/فك حظر)
- 📡 قنوات الاشتراك الإجباري
- 🤖 مساعد ذكاء اصطناعي (OpenRouter)
- 📊 لوحة تحكم متكاملة للمالك

## التقنيات المستخدمة

- **Python 3.10+**
- **aiogram 3.x** - إطار عمل البوت
- **FastAPI** - الخادم الخلفي
- **PostgreSQL** - قاعدة البيانات
- **Redis** - التخزين المؤقت
- **OpenRouter API** - الذكاء الاصطناعي

## التثبيت

### باستخدام Docker (موصى به)

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل الإعدادات في .env

# تشغيل الحاويات
docker-compose up -d
```

### التثبيت اليدوي

```bash
# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows

# تثبيت الحزم
pip install -r requirements.txt

# تشغيل التطبيق
python main.py
```

## الإعدادات

عدّل ملف `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_ADMIN_ID=your_admin_id
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smart_books_db
OPENROUTER_API_KEY=your_api_key
```

## هيكل المشروع

```
smart_books_library_bot/
├── app/
│   ├── admin/         # خدمات الإدارة
│   ├── api/           # واجهات API
│   ├── bot/           # معالجات البوت
│   ├── models/        # نماذج قاعدة البيانات
│   ├── schemas/       # مخططات Pydantic
│   ├── services/      # خدمات الأعمال
│   └── utils/         # أدوات مساعدة
├── config/            # الإعدادات
├── uploads/           # ملفات الكتب
├── main.py            # نقطة الدخول
├── docker-compose.yml
└── Dockerfile
```

## أوامر المالك

| الأمر | الوصف |
|-------|-------|
| `/start` | بدء البوت |
| `/stats` | عرض الإحصائيات |
| `/exportcsv` | تصدير الكتب |
| `/listcategories` | عرض الأقسام |
| `/listauthors` | عرض المؤلفين |
| `/listchannels` | عرض قنوات الاشتراك |
| `/aifind` | بحث ذكي AI |

## لوحة التحكم

توفر لوحة تحكم المالك:

- 📊 إحصائيات متقدمة
- 📚 إدارة الكتب (موافقة/رفض/حذف)
- 📁 إدارة الأقسام والمؤلفين
- 📡 إدارة قنوات الاشتراك
- 🚫 إدارة المستخدمين
- 🤖 مساعد AI
- 📤 رفع وإدارة الكتب

## رخصة الاستخدام

MIT License
