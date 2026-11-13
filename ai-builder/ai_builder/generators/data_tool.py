"""مولّد أداة بيانات: CSV → تنظيف → مخرجات + تقرير."""

from __future__ import annotations

from string import Template

from ..spec import Spec
from .base import Generator

MAIN_TEMPLATE = Template(
    '''#!/usr/bin/env python3
"""$title

$description

مولّد آلياً بواسطة ai-builder.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """قراءة ملف CSV مع ترميز UTF-8."""
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = [dict(row) for row in reader]
        columns = list(reader.fieldnames or [])
    return columns, rows


def clean_rows(
    rows: list[dict[str, str]],
    drop_empty: bool = True,
    dedupe: bool = True,
    trim: bool = True,
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """تنظيف الصفوف وإرجاع الصفوف النظيفة مع إحصاءات."""
    stats = {"input": len(rows), "dropped_empty": 0, "dropped_duplicate": 0, "output": 0}
    cleaned: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()

    for row in rows:
        if trim:
            row = {key: (value or "").strip() for key, value in row.items()}
        if drop_empty and not any(row.values()):
            stats["dropped_empty"] += 1
            continue
        if dedupe:
            signature = tuple(row.get(key, "") for key in sorted(row))
            if signature in seen:
                stats["dropped_duplicate"] += 1
                continue
            seen.add(signature)
        cleaned.append(row)

    stats["output"] = len(cleaned)
    return cleaned, stats


def summarize(columns: list[str], rows: list[dict[str, str]]) -> dict[str, Any]:
    """ملخصQuality: الأعمدة، الصفوف، والقيم الفارغة لكل عمود."""
    missing = {column: 0 for column in columns}
    for row in rows:
        for column in columns:
            if not (row.get(column) or "").strip():
                missing[column] += 1
    return {
        "columns": columns,
        "row_count": len(rows),
        "missing_values": missing,
        "complete_rows": sum(1 for row in rows if all((row.get(c) or "").strip() for c in columns)),
    }


def write_csv(path: Path, columns: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, summary: dict[str, Any], stats: dict[str, int]) -> None:
    lines = [
        "# تقرير المعالجة",
        "",
        f"- الأعمدة: {', '.join(summary['columns']) or '—'}",
        f"- عدد الصفوف بعد التنظيف: {summary['row_count']}",
        f"- صفوف مكتملة: {summary['complete_rows']}",
        "",
        "## إحصاءات التنظيف",
        f"- صفوف مُدخلة: {stats['input']}",
        f"- صفوف فارغة أُسقطت: {stats['dropped_empty']}",
        f"- صفوف مكررة أُسقطت: {stats['dropped_duplicate']}",
        "",
        "## القيم الفارغة لكل عمود",
    ]
    for column, count in summary["missing_values"].items():
        lines.append(f"- {column}: {count}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\\n".join(lines) + "\\n", encoding="utf-8")


def run(input_path: Path, output_dir: Path, drop_empty: bool, dedupe: bool) -> dict[str, Any]:
    columns, rows = read_csv(input_path)
    cleaned, stats = clean_rows(rows, drop_empty=drop_empty, dedupe=dedupe)
    summary = summarize(columns, cleaned)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "cleaned.csv", columns, cleaned)
    (output_dir / "summary.json").write_text(
        json.dumps({"summary": summary, "cleaning": stats}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    write_report(output_dir / "report.md", summary, stats)
    return {"summary": summary, "cleaning": stats, "output_dir": str(output_dir)}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="$name", description="$description")
    parser.add_argument("--input", type=Path, required=True, help="ملف CSV المدخل")
    parser.add_argument("--output-dir", type=Path, default=Path("out"), help="مجلد المخرجات")
    parser.add_argument("--keep-empty", action="store_true", help="عدم إسقاط الصفوف الفارغة")
    parser.add_argument("--keep-duplicates", action="store_true", help="عدم إسقاط الصفوف المكررة")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.input.exists():
        print(f"error: الملف غير موجود: {args.input}", file=sys.stderr)
        return 1
    try:
        result = run(
            args.input,
            args.output_dir,
            drop_empty=not args.keep_empty,
            dedupe=not args.keep_duplicates,
        )
    except csv.Error as exc:
        print(f"error: ملف CSV غير صالح: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''
)

TEST_TEMPLATE = Template(
    '''"""اختبارات $title"""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from $name import clean_rows, read_csv, run, summarize


class TestPipeline(unittest.TestCase):
    def test_clean_rows(self):
        rows = [
            {"name": "  أحمد  ", "city": "الرياض"},
            {"name": "أحمد", "city": "الرياض"},
            {"name": "  ", "city": "  "},
        ]
        cleaned, stats = clean_rows(rows)
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["name"], "أحمد")
        self.assertEqual(stats["dropped_duplicate"], 1)
        self.assertEqual(stats["dropped_empty"], 1)

    def test_summarize(self):
        columns = ["a", "b"]
        rows = [{"a": "1", "b": ""}]
        summary = summarize(columns, rows)
        self.assertEqual(summary["row_count"], 1)
        self.assertEqual(summary["missing_values"]["b"], 1)

    def test_run_writes_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "in.csv"
            with src.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["name", "city"])
                writer.writerow(["سارة", "جدة"])
                writer.writerow(["سارة", "جدة"])
            out = root / "out"
            result = run(src, out, drop_empty=True, dedupe=True)
            self.assertTrue((out / "cleaned.csv").exists())
            self.assertTrue((out / "summary.json").exists())
            self.assertTrue((out / "report.md").exists())
            self.assertEqual(result["cleaning"]["output"], 1)


if __name__ == "__main__":
    unittest.main()
'''
)

SAMPLE_CSV = """name,city,role,notes
أحمد,الرياض,مهندس, 
سارة,جدة,مصممة,مشاريع
أحمد,الرياض,مهندس, 
ليلى,الدمام,محللة,تقارير
سارة,جدة,مصممة,مشاريع
"""


class DataToolGenerator(Generator):
    kind = "data_tool"

    def generate(self, spec: Spec) -> dict[str, str]:
        readme = self.readme(
            spec,
            run=[
                f"python3 {spec.name}.py --input data/sample.csv --output-dir out",
                "python3 -m unittest discover -s tests -t . -v",
            ],
            extra="## المخرجات\n"
            "- `cleaned.csv`: الصفوف بعد التنظيف\n"
            "- `summary.json`: ملخص JSON (الأعمدة، الصفوف، القيم الفارغة)\n"
            "- `report.md`: تقرير Markdown قابل للقراءة\n\n"
            "## المعاملات\n"
            "- `--input`: ملف CSV المدخل (إلزامي)\n"
            "- `--output-dir`: مجلد المخرجات (افتراضياً `out`)\n"
            "- `--keep-empty` / `--keep-duplicates`: تعطيل الإسقاط\n\n",
        )

        return {
            f"{spec.name}.py": MAIN_TEMPLATE.substitute(
                title=spec.title, description=spec.description, name=spec.name
            ),
            "README.md": readme,
            "requirements.txt": self.requirements(),
            "tests/__init__.py": "",
            f"tests/test_{spec.name}.py": TEST_TEMPLATE.substitute(
                title=spec.title, name=spec.name
            ),
            "data/sample.csv": SAMPLE_CSV,
        }
