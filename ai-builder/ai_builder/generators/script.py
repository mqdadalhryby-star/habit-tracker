"""مولّد سكربت أتمتة: يفحص مجلداً ويأخذ نسخاً احتياطية."""

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
import json
import logging
import shutil
import sys
import time
from pathlib import Path

LOGGER = logging.getLogger("$name")


def configure_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def scan_directory(root: Path) -> dict:
    """إحصاء الملفات حسب الامتداد وإجمالي الحجم وأكبر الملفات."""
    summary = {
        "root": str(root),
        "total_files": 0,
        "total_bytes": 0,
        "by_extension": {},
        "largest": [],
    }
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        summary["total_files"] += 1
        size = path.stat().st_size
        summary["total_bytes"] += size
        ext = path.suffix.lower() or "(بلا امتداد)"
        summary["by_extension"][ext] = summary["by_extension"].get(ext, 0) + 1
        summary["largest"].append({"path": str(path), "bytes": size})
    summary["largest"].sort(key=lambda item: item["bytes"], reverse=True)
    summary["largest"] = summary["largest"][:5]
    return summary


def backup_files(
    root: Path,
    destination: Path,
    days: int = 7,
    dry_run: bool = True,
    copy: bool = True,
) -> dict:
    """نسخ الملفات المعدّلة خلال آخر days يوماً إلى مجلد الوجهة."""
    cutoff = time.time() - days * 86400
    destination.mkdir(parents=True, exist_ok=True)
    copied, skipped = [], []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.stat().st_mtime < cutoff:
            skipped.append(str(path))
            continue
        target = destination / path.relative_to(root)
        if dry_run:
            copied.append(str(target))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if copy:
            shutil.copy2(path, target)
        else:
            shutil.move(str(path), str(target))
        copied.append(str(target))
    return {
        "copied": copied,
        "skipped": skipped,
        "destination": str(destination),
        "dry_run": dry_run,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="$name",
        description="$description",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="فحص محتويات مجلد")
    scan.add_argument("path", type=Path, help="المجلد المراد فحصه")

    backup = sub.add_parser("backup", help="أخذ نسخة احتياطية من الملفات الحديثة")
    backup.add_argument("path", type=Path, help="مجلد المصدر")
    backup.add_argument("-d", "--destination", type=Path, default=Path("backup"), help="مجلد الوجهة")
    backup.add_argument("--days", type=int, default=7, help="الفترة بالأيام")
    backup.add_argument("--execute", action="store_true", help="تنفيذ فعلي (بدونه وضع تجريبي)")
    backup.add_argument("--move", action="store_true", help="نقل بدل النسخ")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()

    if args.command == "scan":
        if not args.path.is_dir():
            print(f"error: المجلد غير موجود: {args.path}", file=sys.stderr)
            return 1
        summary = scan_directory(args.path)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    if args.command == "backup":
        if not args.path.is_dir():
            print(f"error: المجلد غير موجود: {args.path}", file=sys.stderr)
            return 1
        result = backup_files(
            args.path,
            args.destination,
            days=args.days,
            dry_run=not args.execute,
            copy=not args.move,
        )
        LOGGER.info(
            "%s %d ملف إلى %s",
            "سيتم نسخ" if result["dry_run"] else "تم نسخ",
            len(result["copied"]),
            result["destination"],
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
'''
)

TEST_TEMPLATE = Template(
    '''"""اختبارات $title"""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from $name import backup_files, scan_directory


class TestScript(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "a.txt").write_text("alpha", encoding="utf-8")
        (self.root / "b.txt").write_text("beta", encoding="utf-8")
        (self.root / "sub").mkdir()
        (self.root / "sub" / "c.md").write_text("gamma", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_scan_counts_files(self):
        summary = scan_directory(self.root)
        self.assertEqual(summary["total_files"], 3)
        self.assertEqual(summary["by_extension"].get(".txt"), 2)
        self.assertEqual(summary["by_extension"].get(".md"), 1)

    def test_backup_dry_run(self):
        with tempfile.TemporaryDirectory() as dest:
            result = backup_files(self.root, Path(dest), days=3650, dry_run=True)
            self.assertEqual(len(result["copied"]), 3)
            self.assertTrue(result["dry_run"])
            self.assertEqual(list(Path(dest).iterdir()), [])

    def test_backup_executes(self):
        with tempfile.TemporaryDirectory() as dest:
            result = backup_files(self.root, Path(dest), days=3650, dry_run=False)
            self.assertEqual(len(result["copied"]), 3)
            self.assertTrue((Path(dest) / "sub" / "c.md").exists())


if __name__ == "__main__":
    unittest.main()
'''
)


class ScriptGenerator(Generator):
    kind = "script"

    def generate(self, spec: Spec) -> dict[str, str]:
        readme = self.readme(
            spec,
            run=[
                f"python3 {spec.name}.py scan .",
                f"python3 {spec.name}.py backup . -d backup --days 7",
                f"python3 {spec.name}.py backup . -d backup --days 7 --execute",
                "python3 -m unittest discover -s tests -t . -v",
            ],
            extra="## الأوامر\n"
            "- `scan <path>`: إحصاء الملفات حسب الامتداد والحجم وأكبر 5 ملفات\n"
            "- `backup <path> -d <dest>`: نسخ الملفات المعدّلة خلال آخر `--days` يوماً\n"
            "  - بدون `--execute` يعمل في وضع تجريبي (لا يكتب شيئاً)\n"
            "  - `--move` ينقل الملفات بدل نسخها\n\n",
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
        }
