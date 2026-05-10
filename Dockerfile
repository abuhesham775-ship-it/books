# Dockerfile
# Smart Books Library Bot
# force rebuild 2026-05-04
# استخدام صورة Python الرسمية
FROM python:3.11-slim

# تعيين متغيرات البيئة
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# إنشاء مجلد التطبيق
WORKDIR /app

# تحديث الحزم
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# نسخ ملفات المشروع
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات
COPY . .

# إنشاء مجلدات مطلوبة
RUN mkdir -p /app/uploads /app/logs

# إعطاء الصلاحيات
RUN chmod +x /app

# كشف المنفذ
EXPOSE 8000

# أمر التشغيل
CMD ["python", "main.py"]
