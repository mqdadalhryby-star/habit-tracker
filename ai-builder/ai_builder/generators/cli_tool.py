"""مولّد أداة سطر الأوامر: ينتج أداة معالجة نصوص حقيقية تعمل فوراً."""

from __future__ import annotations

from string import Template

from ..spec import Spec
from .base import Generator

# اسم العملية -> (الوصف، تعبير المعالجة، كود الاختبار)
OPS: dict[str, tuple[str, str, str]] = {
    "uppercase": (
        "تحويل كل سطر إلى حروف كبيرة",
        "lambda lines: [l.upper() for l in lines]",
        "self.assertEqual(apply_operation(['ab', 'cd'], 'uppercase'), ['AB', 'CD'])",
    ),
    "lowercase": (
        "تحويل كل سطر إلى حروف صغيرة",
        "lambda lines: [l.lower() for l in lines]",
        "self.assertEqual(apply_operation(['AB'], 'lowercase'), ['ab'])",
    ),
    "reverse": (
        "عكس ترتيب الأحرف داخل كل سطر",
        "lambda lines: [l[::-1] for l in lines]",
        "self.assertEqual(apply_operation(['ab'], 'reverse'), ['ba'])",
    ),
    "sort": (
        "ترتيب السطور أبجدياً",
        "lambda lines: sorted(lines)",
        "self.assertEqual(apply_operation(['b', 'a'], 'sort'), ['a', 'b'])",
    ),
    "unique": (
        "إزالة السطور المكررة مع الحفاظ على الترتيب",
        "lambda lines: list(dict.fromkeys(lines))",
        "self.assertEqual(apply_operation(['a', 'a', 'b'], 'unique'), ['a', 'b'])",
    ),
    "trim": (
        "إزالة المسافات الزائدة من طرفي كل سطر",
        "lambda lines: [l.strip() for l in lines]",
        "self.assertEqual(apply_operation(['  a  '], 'trim'), ['a'])",
    ),
    "count": (
        "قراءة الملف وإحصاء سطوره",
        "lambda lines: list(lines)",
        "self.assertEqual(len(apply_operation(['a', 'b'], 'count')), 2)",
    ),
    "filter": (
        "تجاهل السطور الفارغة",
        "lambda lines: [l for l in lines if l.strip()]",
        "self.assertEqual(apply_operation(['', 'a'], 'filter'), ['a'])",
    ),
    "json_format": (
        "تنسيق ملف JSON بإزاحة بعينين",
        "lambda lines: [json.dumps(json.loads(chr(10).join(lines)), ensure_ascii=False, indent=2)]",
        "self.assertIn('\"a\": 1', apply_operation(['{\"a\": 1}'], 'json_format')[0])",
    ),
    "summarize": (
        "عرض ملخص بأول وآخر سطر",
        "lambda lines: ([lines[0]] if lines else []) + (['...'] if len(lines) > 2 else []) + ([lines[-1]] if len(lines) > 1 else [])",
        "self.assertTrue(apply_operation(['a', 'b'], 'summarize'))",
    ),
}

MAIN_TEMPLATE = Template(
    '''#!/usr/bin/env python3
"""$title

$description

مولّد آلياً بواسطة ai-builder.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# العمليات المتاحة: الاسم -> (الوصف، دالة المعالجة)
OPERATIONS: dict[str, tuple[str, object]] = {
$ops_block
}


def available_operations() -> list[str]:
    return list(OPERATIONS)


def apply_operation(lines: list[str], op: str) -> list[str]:
    """تنفيذ عملية على قائمة أسطر."""
    if op not in OPERATIONS:
        raise KeyError(op)
    handler = OPERATIONS[op][1]
    return handler(lines)


def read_lines(path: Path) -> list[str]:
    """قراءة الملف بترميز UTF-8."""
    return path.read_text(encoding="utf-8").splitlines()


def write_lines(path: Path, lines: list[str]) -> None:
    """كتابة الأسطر إلى ملف."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\\n".join(lines)
    path.write_text(body + ("\\n" if body else ""), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="$name",
        description="$description",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""العمليات المتاحة:
$ops_help""",
    )
    parser.add_argument("input", type=Path, help="الملف المراد معالجته")
    parser.add_argument("-o", "--output", type=Path, default=None, help="ملف الإخراج (افتراضياً: stdout)")
    parser.add_argument("--op", choices=$choices, default="$default_op", help="العملية المراد تنفيذها")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"error: الملف غير موجود: {args.input}", file=sys.stderr)
        return 1
    try:
        lines = read_lines(args.input)
        result = apply_operation(lines, args.op)
    except KeyError:
        print(f"error: عملية غير معروفة: {args.op}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"error: JSON غير صالح: {exc}", file=sys.stderr)
        return 1

    if args.output and args.op != "count":
        write_lines(args.output, result)
        print(f"تم: {args.input} -> {args.output} ({len(result)} سطر)")
    else:
        for line in result:
            print(line)
    print(f"إحصاءات: {len(lines)} سطر مُدخل، {len(result)} سطر ناتج")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
)

TEST_TEMPLATE = Template(
    '''"""اختبارات $title"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from $name import apply_operation, available_operations, read_lines, write_lines


class TestOperations(unittest.TestCase):
    def test_operations_registered(self):
        self.assertTrue(available_operations())
        self.assertIn("$default_op", available_operations())

$test_cases

    def test_file_roundtrip(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "in.txt"
            dst = Path(tmp) / "out.txt"
            write_lines(src, ["سطر أول", "سطر ثانٍ"])
            lines = read_lines(src)
            self.assertEqual(len(lines), 2)
            write_lines(dst, apply_operation(lines, "$default_op"))
            self.assertTrue(dst.exists())


if __name__ == "__main__":
    unittest.main()
'''
)


class CLIToolGenerator(Generator):
    kind = "cli_tool"

    def generate(self, spec: Spec) -> dict[str, str]:
        selected = [op for op in spec.operations if op in OPS] or ["count"]
        # نضيف upper/lower فقط عند وجودهما صراحةً، وأبقي القائمة غير فارغة
        default_op = selected[0]

        ops_lines = []
        for op in selected:
            label, handler, _ = OPS[op]
            ops_lines.append(f'    "{op}": ("{label}", {handler}),')
        ops_block = "\n".join(ops_lines)

        ops_help = "\n".join(f"  {op:<12} {OPS[op][0]}" for op in selected)
        choices = "[" + ", ".join(f'"{op}"' for op in selected) + "]"

        test_cases = "\n".join(
            f"    def test_{op}(self):\n        {OPS[op][2]}" for op in selected
        )

        main_code = MAIN_TEMPLATE.substitute(
            title=spec.title,
            description=spec.description,
            name=spec.name,
            ops_block=ops_block,
            ops_help=ops_help,
            choices=choices,
            default_op=default_op,
        )
        test_code = TEST_TEMPLATE.substitute(
            title=spec.title, name=spec.name, default_op=default_op, test_cases=test_cases
        )

        sample = "سطر تجريبي أول\nسطر تجريبي ثاني\nسطر تجريبي ثالث\n"
        readme = self.readme(
            spec,
            run=[
                f"python3 {spec.name}.py data/sample.txt --op {default_op}",
                f"python3 {spec.name}.py data/sample.txt --op {default_op} -o out.txt",
                "python3 -m unittest discover -s tests -t . -v",
            ],
            extra="## المعاملات\n"
            "- `input`: مسار الملف المراد معالجته (إلزامي)\n"
            "- `-o/--output`: ملف الإخراج؛ إن لم يُحدَّد تُطبع النتيجة على الشاشة\n"
            "- `--op`: العملية المراد تنفيذها\n\n"
            "## العمليات المتاحة\n"
            + "\n".join(f"- `{op}`: {OPS[op][0]}" for op in selected)
            + "\n\n",
        )

        return {
            f"{spec.name}.py": main_code,
            "README.md": readme,
            "requirements.txt": self.requirements(),
            "tests/__init__.py": "",
            f"tests/test_{spec.name}.py": test_code,
            "data/sample.txt": sample,
        }
