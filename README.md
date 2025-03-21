# ربات تلگرام Hoomak برای ثبت محصول در ووکامرس

این پروژه یه ربات تلگرام به نام **Hoomak** هست که برای ثبت محصولات متغیر (Variable Products) توی فروشگاه ووکامرسی طراحی شده. ربات اطلاعات محصول رو از کاربر می‌گیره، یه JSON می‌سازه و با استفاده از REST API ووکامرس، محصول رو توی سایت ثبت می‌کنه. همچنین قابلیت آپلود عکس‌ها روی هاست سایت و مدیریت ویژگی‌های محصول (مثل سایز، رنگ و ...) رو داره.

## ویژگی‌های اصلی

- **گرفتن اطلاعات محصول از کاربر**:
  - عنوان، توضیحات، عکس شاخص و گالری، سایزها، رنگ، جنس رویه، جنس زیره، کاربرد، SKU، قیمت، تگ‌ها (اختیاری) و برند.
- **مدیریت ویژگی‌ها (Attributes)**:
  - ویژگی‌ها (مثل سایز، رنگ و ...) به صورت Global Attributes توی ووکامرس تعریف شدن.
  - کاربر می‌تونه از مقادیر موجود انتخاب کنه یا مقدار جدید اضافه کنه.
  - مقادیر به صورت دکمه‌های شیشه‌ای (Inline Keyboard) و به شکل عمودی نمایش داده می‌شن.
- **آپلود عکس‌ها**:
  - عکس‌ها با API وردپرس (`/wp/v2/media`) روی هاست سایت آپلود می‌شن.
- **ساخت و ثبت محصول**:
  - ربات یه JSON برای محصول می‌سازه و با API ووکامرس (`/wp-json/wc/v3/products`) ثبت می‌کنه.
  - تنوع‌ها (Variations) با API جداگونه اضافه می‌شن.
  - `permalink` محصول برابر با `sku` تنظیم می‌شه.
- **نمایش خلاصه**:
  - به جای JSON، یه خلاصه از ورودی‌ها نمایش داده می‌شه و کاربر می‌تونه تأیید یا لغو کنه.

## پیش‌نیازها

- **پایتون**: نسخه 3.11 یا بالاتر
- **وابستگی‌ها**:
  - `python-telegram-bot[webhooks]==20.8`
  - `requests`
  - `python-dotenv`
- **تلگرام**:
  - یه ربات تلگرام (با توکن از BotFather)
- **ووکامرس**:
  - یه سایت وردپرسی با ووکامرس فعال
  - کلیدهای API ووکامرس (Consumer Key و Consumer Secret)
  - Application Password برای آپلود عکس‌ها
- **render.com**:
  - برای دیپلوی ربات (یا هر سرویس میزبانی دیگه)

## نصب و راه‌اندازی

1. **کلون کردن مخزن**:
   ```bash
   git clone https://github.com/TheAyrik/Hoomak.git
   cd Hoomak