# Habit Tracker — متتبع العادات

تطبيق ويب عربي (RTL) لمتابعة العادات اليومية، **مولَّد آلياً** بواسطة نموذج `ai-builder` المرفق في هذا المستودع.

🔗 **النسخة المباشرة:** <https://ayzgo6vda9g2k.space.mcode.io>

![لقطة من التطبيق](docs/screenshot.png)

## المزايا
- إضافة عناصر العادات وتعليمها كمكتملة بنقرة واحدة.
- تصفية: الكل / غير منتهٍ / منتهٍ.
- حفظ تلقائي في `localStorage` — البيانات تبقى بعد إعادة التحميل أو إغلاق المتصفح.
- واجهة عربية RTL متجاوبة مع الجوال، بلا أي تبعيات أو عملية بناء.

## التشغيل المحلي
```bash
python3 -m http.server 8000
# ثم افتح http://localhost:8000
```

## نموذج `ai-builder` (مولّد المشاريع)
النموذج الذي أنشأ هذا التطبيق موجود داخل `ai-builder/` — بلا تبعيات خارجية (مكتبة بايثون القياسية فقط).

```bash
cd ai-builder

# بناء مشروع جديد من وصف نصي (مع تشغيل اختبارات المشروع المولَّد تلقائياً)
python3 -m ai_builder build "أنشئ لي أداة تنظف ملفات CSV وتنتج تقريراً" --out ./generated

# الأنواع المدعومة
python3 -m ai_builder kinds

# فحص البيئة والإعدادات
python3 -m ai_builder doctor

# تفعيل النموذج اللغوي (اختياري) — MiniMax أو أي مزوّد متوافق مع OpenAI
export MINIMAX_API_KEY=sk-...
python3 -m ai_builder build "..." --provider minimax --model MiniMax-M3.1-Flash
```

### الأنواع المدعومة
| النوع | الناتج |
|---|---|
| `cli_tool` | أداة سطر أوامر بمعالجة نصوص حقيقية |
| `web_app` | تطبيق ويب صفحة واحدة (RTL) بلا تبعيات |
| `api_service` | خدمة FastAPI: منطق نقي + نقاط CRUD + توثيق `/docs` |
| `script` | سكربت أتمتة: فحص مجلد + نسخ احتياطي بوضع تجريبي |
| `data_tool` | خط أنابيب بيانات: CSV ← تنظيف ← مخرجات + تقرير |

## الاختبارات
```bash
cd ai-builder
python3 -m unittest discover -s tests -t . -v
```
تشمل اختبارات end-to-end تبني كل نوع مشروع في مجلد مؤقت ثم **تشغّل اختبارات المشروع المولَّد فعلياً** وتتحقق من مخرجاته.

## بنية المستودع
```
habit-tracker/
├── index.html              # واجهة التطبيق (نهاية السطر الأولى → تعمل مع Pages من main/root)
├── styles.css              # الثيم الداكن المتجاوب
├── app.js                  # منطق التطبيق + التخزين المحلي
├── .github/workflows/      # نشر تلقائي إلى GitHub Pages
├── .nojekyll               # يمنع معالجة Jekyll
├── docs/screenshot.png     # لقطة من التطبيق
└── ai-builder/             # نموذج توليد المشاريع (مصدر بايثون + اختبارات)
```

## النشر على GitHub Pages
المستودع يحتوي على `/.github/workflows/pages.yml` للنشر التلقائي. بعد الدفع إلى `main`:
1. من **Settings ← Pages** اختر المصدر: **GitHub Actions** (أو `Deploy from a branch ← main / (root)`).
2. أول تشغيل للـ workflow ينشر الموقع على `https://<حسابك>.github.io/habit-tracker/`.

> ملاحظة: مجلد `ai-builder/` يُنشر أيضاً مع بقية الملفات كملفات ساكنة — لا يؤثر على عمل الموقع.

## الترخيص
MIT — استخدمه وعدّله كما تشاء.
