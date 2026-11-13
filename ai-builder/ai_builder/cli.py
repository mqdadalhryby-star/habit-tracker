"""واجهة سطر الأوامر لـ ai-builder."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .llm import PROVIDERS, build_backend, load_config, save_config
from .model import BuilderModel
from .spec import KIND_LABELS, KINDS


def _print_plan(spec) -> None:
    print("── خطة التنفيذ " + "─" * 44)
    print(f"النوع      : {spec.kind_label} ({spec.kind})")
    print(f"الاسم      : {spec.name}")
    print(f"العنوان    : {spec.title}")
    print(f"العمليات   : {', '.join(spec.operations) or '—'}")
    print(f"الكيانات   : {', '.join(spec.entities) or '—'}")
    print(f"المصدر     : {spec.source}")
    print()


def cmd_build(args: argparse.Namespace) -> int:
    backend = build_backend(
        provider=args.provider,
        model=args.model,
        base_url=args.base_url,
        api_key=args.api_key,
    )
    model = BuilderModel(backend=backend, verify=not args.no_verify)
    spec = model.plan(args.request)
    if args.kind:
        spec.kind = args.kind
    _print_plan(spec)

    result = model.build(args.request, out_dir=args.out, kind=args.kind, force=args.force)

    if args.json:
        print(
            json.dumps(
                {
                    "spec": result.spec.to_dict(),
                    "project_dir": str(result.project_dir),
                    "files": [str(f) for f in result.files],
                    "verification": [v.as_dict() for v in result.verification],
                    "notes": result.notes,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if result.ok else 1

    print("── النتيجة " + "─" * 47)
    print(f"النوع     : {result.spec.kind_label}")
    print(f"المجلد    : {result.project_dir}")
    print(f"الملفات   : {len(result.files)}")
    print(f"التشغيل   : {result.spec.entrypoint}")
    for verification in result.verification:
        mark = "OK  " if verification.ok else "FAIL"
        print(f"[{mark}] {verification.name}")
        if not verification.ok and verification.output:
            for line in verification.output.splitlines()[-6:]:
                print(f"        {line}")
    for note in result.notes:
        print(f"ملاحظة: {note}")
    print(f"\nالمجلد الجاهز: {result.project_dir}")
    return 0 if result.ok else 1


def cmd_kinds(args: argparse.Namespace) -> int:
    for kind in KINDS:
        print(f"{kind:<12} {KIND_LABELS[kind]}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    values = load_config()
    if args.api_key:
        values[f"{args.provider}_api_key" if args.provider != "auto" else "minimax_api_key"] = args.api_key
    if args.base_url:
        values["base_url"] = args.base_url
    if args.model:
        values["model"] = args.model
    if args.provider and args.provider != "auto":
        values["provider"] = args.provider
    path = save_config(values)
    print(f"تم حفظ الإعداد في {path}")
    print("المفتاح محفوظ محلياً (صلاحية 600) ولا يُطبع في أي مخرجات.")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    print(f"Python     : {sys.version.split()[0]}")
    backend = build_backend(provider=args.provider)
    if backend.available():
        print(f"النموذج LLM: مفعّل ({backend.name} / {getattr(backend, 'model', '-')})")
    else:
        print("النموذج LLM: غير مفعّل — سيعمل المحرك القواعدي المحلي")
        print("             للتفعيل: ai-builder config --api-key <KEY>")
    print(f"المزوّدون  : {', '.join(PROVIDERS)}")
    try:
        import pandas  # noqa: F401

        print("pandas     : متوفر")
    except ImportError:
        print("pandas     : غير مثبّت (المشاريع المولّدة لا تحتاجه)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-builder",
        description="نموذج ذكاء اصطناعي يحوّل وصفاً نصياً إلى مشروع قابل للتشغيل.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="بناء مشروع من طلب نصي")
    build.add_argument("request", help="وصف المشروع المطلوب")
    build.add_argument("--out", default="./generated", help="مجلد الإخراج")
    build.add_argument("--kind", choices=KINDS, help="فرض نوع المشروع")
    build.add_argument("--provider", default="auto", help="minimax | openai | none | auto")
    build.add_argument("--model", help="اسم النموذج")
    build.add_argument("--base-url", help="عنوان الـ API")
    build.add_argument("--api-key", help="مفتاح الـ API")
    build.add_argument("--force", action="store_true", help="الكتابة فوق المجلد إن وُجد")
    build.add_argument("--no-verify", action="store_true", help="تخطي تشغيل الاختبارات")
    build.add_argument("--json", action="store_true", help="إخراج JSON")
    build.set_defaults(func=cmd_build)

    kinds = sub.add_parser("kinds", help="عرض أنواع المشاريع المدعومة")
    kinds.set_defaults(func=cmd_kinds)

    config = sub.add_parser("config", help="حفظ إعدادات النموذج اللغوي")
    config.add_argument("--api-key", help="مفتاح الـ API")
    config.add_argument("--base-url", help="عنوان الـ API")
    config.add_argument("--model", help="اسم النموذج")
    config.add_argument("--provider", default="auto", help="minimax | openai")
    config.set_defaults(func=cmd_config)

    doctor = sub.add_parser("doctor", help="فحص البيئة والإعدادات")
    doctor.add_argument("--provider", default="auto")
    doctor.set_defaults(func=cmd_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
