# ai-builder — نموذج ذكاء اصطناعي يصنع أدوات وبرامج ومشاريع

> ## 🖥 المنصة (Studio) — واجهة ويب تستقبل أوامرَك
> ```bash
> python3 studio/server.py      # ثم افتح http://localhost:8000
> ```
> اكتب أمراً ← تُولَّد المشروع مع اختباراته ← معاينة حيّة + تحميل ZIP. [التفاصيل](studio/README.md)

نموذج عملي يحوّل **وصفاً نصياً** إلى **مشروع كامل يعمل**: كود، اختبارات، توثيق، وملفات تشغيل.
يشتغل بمحركين معاً:
- **محرك قواعدي محلي** (يعمل دائماً بلا إنترنت): يفهم الطلب، يحدد النوع والعمليات، ويولّد المشروع.
- **نموذج لغوي LLM** (اختياري): يحسّن المواصفة والمزايا والاسم عبر MiniMax أو أي مزوّد متوافق مع OpenAI.

## أنواع المشاريع المدعومة
| النوع | ماذا يولّد |
|---|---|
| `cli_tool` | أداة سطر أوامر بمعالجة نصوص حقيقية (uppercase, sort, unique, json_format, …) |
| `web_app` | تطبيق ويب صفحة واحدة (RTL عربي) بتخزين محلي وتصفية، بلا تبعيات |
| `api_service` | خدمة FastAPI: منطق نقي + نقاط CRUD + توثيق `/docs` |
| `script` | سكربت أتمتة: فحص مجلد + نسخ احتياطي بوضع تجريبي آمن |
| `data_tool` | خط أنابيب بيانات: CSV → تنظيف → `cleaned.csv` + `summary.json` + `report.md` |

## التشغيل السريع
```bash
cd ai-builder

# بناء مشروع من طلب نصي (مع تشغيل اختبارات المشروع المولَّد تلقائياً)
python3 -m ai_builder build "أنشئ لي أداة تنظف ملفات CSV وتنتج تقريراً" --out ./generated

# أنواع مدعومة
python3 -m ai_builder kinds

# فحص البيئة
python3 -m ai_builder doctor

# تفعيل النموذج اللغوي (يُحفظ المفتاح محلياً بصلاحية 600)
python3 -m ai_builder config --api-key sk-xxxx --provider minimax
export MINIMAX_API_KEY=sk-xxxx   # أو ضع المفتاح في المتغير
```

## خيارات البناء
| الخيار | الوظيفة |
|---|---|
| `--out DIR` | مجلد الإخراج (افتراضياً `./generated`) |
| `--kind KIND` | فرض نوع المشروع بعينه |
| `--provider` | `minimax` / `openai` / `none` / `auto` |
| `--model` | اسم النموذج اللغوي |
| `--base-url` / `--api-key` | تخصيص نقطة الاتصال والمفتاح |
| `--no-verify` | تخطي تشغيل اختبارات المشروع المولَّد |
| `--force` | الكتابة فوق المجلد إن وُجد |
| `--json` | إخراج JSON للمعالجة الآلية |

## كيف يعمل
```
طلب المستخدم
   │
   ├─ intent.analyze()  ──►  Spec {kind, name, title, operations, entities, features}
   │        ▲
   │        └── llm.OpenAICompatBackend  (تحسين المواصفة إن توفّر مفتاح)
   ▼
generators.get_generator(kind).generate(spec)  ──►  {ملف: محتوى}
   ▼
كتابة الملفات + تشغيل اختبارات المشروع المولَّد (تحقق تلقائي)
   ▼
BuildResult { project_dir, files, verification, notes }
```

## البنية
```
ai-builder/
├── ai_builder/
│   ├── intent.py       # محرك النية (قواعدي، بلا تبعيات)
│   ├── llm.py          # طبقة LLM المتوافقة مع OpenAI (MiniMax افتراضياً)
│   ├── model.py        # النموذج: تخطيط ← توليد ← تحقق
│   ├── spec.py         # dataclass المواصفة
│   ├── cli.py          # واجهة سطر الأوامر
│   └── generators/     # مولّد لكل نوع مشروع
└── tests/              # 17 اختباراً (تشمل توليد كل نوع وتشغيل اختباراته)
```

## الاختبارات
```bash
python3 -m unittest discover -s tests -t . -v
```
تشمل اختبارات end-to-end تبني كل نوع مشروع في مجلد مؤقت ثم **تشغّل اختبارات المشروع المولَّد فعلياً** وتتحقق من مخرجاته.

## إضافة نوع مشروع جديد
1. أنشئ `ai_builder/generators/my_kind.py` يرث من `Generator` ويعيد خريطة ملفات.
2. سجّله في `ai_builder/generators/__init__.py`.
3. أضف نمط الكلمات في `intent.py` ووسماً في `spec.KIND_LABELS`.

## نصوص LLM

الواجهة متوافقة مع OpenAI، فالأي من هذه يعمل:
```bash
export MINIMAX_API_KEY=sk-...            # MiniMax: https://api.minimax.io/v1
export OPENAI_API_KEY=sk-...             # OpenAI
python3 -m ai_builder build "..." --provider minimax --model MiniMax-M3.1-Flash
```

> المشروع بلا تبعيات خارجية: مكتبة بايثون القياسية فقط. المشاريع المولَّدة من نوع `api_service` تحتاج `pip install -r requirements.txt` (fastapi + uvicorn) قبل التشغيل.
