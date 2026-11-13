# منصة بناء الأدوات — AiBuilder Studio

منصة ويب تستقبل **أوامر نصية** وتولّد منها مشاريع تعمل: كود + اختبارات + توثيق، مع معاينة حيّة وتحميل ZIP.

```bash
# من جذر مستودع ai-builder
python3 studio/server.py
# ثم افتح: http://localhost:8000
```
بلا أي تثبيت: مكتبة بايثون القياسية فقط (Python 3.10+).

## كيف تعمل
```
الأمر النصي
   │  POST /api/build
   ▼
ai_builder → تخطيط (محرك قواعدي + LLM اختياري) ← توليد الملفات ← تشغيل اختبارات المشروع المولَّد
   │
   ▼
الواجهة تعرض: خطة التنفيذ · شارات التحقق · شجرة الملفات · عارض الكود · معاينة حيّة · تحميل ZIP
```

## نقاط API
| الطريقة | المسار | الوظيفة |
|---|---|---|
| GET | `/` | واجهة المنصة |
| POST | `/api/build` | بناء مشروع: `{request, kind?, provider?, verify?}` |
| GET | `/api/status` | حالة الخادم والنموذج اللغوي والأنواع المدعومة |
| GET | `/api/projects` | قائمة المشاريع المولَّدة + سجل الأوامر |
| GET | `/api/files?name=&path=` | شجرة الملفات أو محتوى ملف |
| GET | `/api/download?name=` | تحميل المشروع كـ ZIP |
| GET | `/preview/<project>/<path>` | معاينة ملفات المشروع المولَّد (iframe) |
| POST | `/api/config` | حفظ مفتاح LLM: `{api_key?, model?}` |

## تفعيل النموذج اللغوي
من زر **⚙ الإعدادات** في الواجهة، أو مباشرة:
```bash
export MINIMAX_API_KEY=sk-...      # يُقرأ تلقائياً
```
يُحفظ المفتاح في `~/.config/ai-builder/config.json` بصلاحية `600`. بلا مفتاح تعمل المنصة بالمحرك القواعدي المحلي (كامل，功能).

## الاختبارات
```bash
cd .. && python3 -m unittest tests.test_platform -v
```
تشغّل الخادم فعلياً على منفذ عشوائي وتختبر: الواجهة، البناء لكل نوع، المعاينة، التنزيل، وحجب `path traversal`.

## النشر على خادم عام
```bash
docker build -f studio/Dockerfile -t ai-builder-studio .
docker run -p 8000:8000 -v "$PWD/studio/generated:/app/generated" ai-builder-studio
```
أو اربط مستودعك في [Render](https://render.com) عبر `studio/render.yaml` (نقرة واحدة) — الملف يجهّز الخدمة ويفتح المنفذ 8000 تلقائياً.
