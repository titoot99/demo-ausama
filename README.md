# demo-ausama — Service Desk Demo

لوحة طلبات صيانة متجاوبة باستخدام Flask وSQLite.

## المزايا
- تسجيل دخول مع hashing لكلمات المرور وجلسات Flask
- CSRF protection
- طلبات صيانة: العنوان، الموقع، الوصف، الأولوية والحالة
- الحالات: جديد، قيد التنفيذ، مكتمل
- بحث وتصفية
- 6 طلبات تجريبية
- اختبارات pytest
- الأسرار وقاعدة البيانات مستثناة من Git

## التشغيل
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/macOS
flask --app app init-db
flask --app app run
```

الحساب التجريبي: admin / ChangeMe123! — غيّره قبل أي استخدام حقيقي.
