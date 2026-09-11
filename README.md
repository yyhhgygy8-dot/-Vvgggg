# V2Ray / Xray Auto Panel

پنل تبدیل‌شده برای ساخت واقعی کاربران **VLESS + WebSocket** با هسته Xray.

## امکانات
- نصب خودکار Xray در Docker image
- ساخت UUID واقعی برای هر کاربر
- دکمه انتخاب حجم (متادیتای پلن؛ برای اعمال واقعی ترافیک نیاز به Xray API/Accounting یا کنترل بیرونی است)
- تاریخ انقضا و غیرفعال‌سازی خودکار
- لینک VLESS و QR
- لینک Subscription با Base64
- ذخیره دائمی SQLite در volume
- اعمال خودکار config و تست Xray قبل از اجرا

## اجرا
`docker compose -f docker-compose.real.yml up -d --build`

قبل از استفاده، `PUBLIC_HOST` را روی IP یا دامنه واقعی سرور قرار دهید و رمز مدیر را تغییر دهید.
