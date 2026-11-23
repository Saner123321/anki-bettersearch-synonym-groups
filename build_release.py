import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "bettersearch_synonym_groups"
PACKAGE = ROOT / "bettersearch_synonym_groups.ankiaddon"
FILES = (
    "__init__.py",
    "config.json",
    "highlights.js",
    "highlights.py",
    "i18n.py",
    "manifest.json",
    "rules.py",
    "search.py",
    "updater.py",
    "wordlist_sync.py",
)


def build():
    manifest = json.loads((SOURCE / "manifest.json").read_bytes())
    with TemporaryDirectory(dir=ROOT, prefix="build-addon-") as folder:
        archive_path = Path(folder) / PACKAGE.name
        with ZipFile(archive_path, "w", ZIP_DEFLATED) as archive:
            for name in FILES:
                archive.write(SOURCE / name, name)
        descriptor = {
            "version": manifest["human_version"],
            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        }
        descriptor_path = Path(folder) / "update.json"
        descriptor_path.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
        archive_path.replace(PACKAGE)
        descriptor_path.replace(ROOT / descriptor_path.name)


if __name__ == "__main__":
    build()
