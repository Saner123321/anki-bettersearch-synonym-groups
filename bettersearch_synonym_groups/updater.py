from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import logging
from pathlib import Path, PurePosixPath
import re
from urllib.request import urlopen
from zipfile import ZipFile

from aqt.addons import InstallOk
from aqt.utils import askUser, showInfo, showWarning


PACKAGE = "bettersearch_synonym_groups"
GITHUB_RAW = "https://raw.githubusercontent.com/Saner123321/anki-bettersearch-synonym-groups"
MAX_PACKAGE_SIZE = 4 * 1024 * 1024
VERSION = re.compile(r"(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})\.(0|[1-9][0-9]{0,5})")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Update:
    version: str
    package: bytes


def version_fields(version):
    if not isinstance(version, str) or not (match := VERSION.fullmatch(version)):
        raise ValueError("Invalid release version")
    return tuple(map(int, match.groups()))


def installed_version():
    manifest = Path(__file__).with_name("manifest.json")
    return json.loads(manifest.read_bytes())["human_version"]


def download(url, limit):
    with urlopen(url, timeout=10) as response:
        if response.geturl() != url:
            raise ValueError("Unexpected update redirect")
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Update file exceeds the size limit")
    return data


def validate_package(package, version):
    with ZipFile(BytesIO(package)) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)) or sum(e.file_size for e in entries) > MAX_PACKAGE_SIZE:
            raise ValueError("Invalid update archive")
        for name in names:
            path = PurePosixPath(name)
            if (
                not path.parts
                or path.is_absolute()
                or ".." in path.parts
                or any(part.casefold() in {"meta.json", "user_files"} for part in path.parts)
                or "\\" in name
                or ":" in name
            ):
                raise ValueError("Unexpected file in update archive")
        if "__init__.py" not in names or "config.json" not in names:
            raise ValueError("Incomplete add-on package")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("package") != PACKAGE or manifest.get("human_version") != version:
            raise ValueError("The update archive identifies a different add-on or version")
        if archive.testzip() is not None:
            raise ValueError("Corrupt update archive")


def check_for_update(current):
    published = json.loads(download(f"{GITHUB_RAW}/main/update.json", 4096))
    version = published["version"]
    if version_fields(version) <= version_fields(current):
        return None

    checksum = published["sha256"]
    if not isinstance(checksum, str) or not re.fullmatch(r"[0-9a-f]{64}", checksum):
        raise ValueError("Invalid update checksum")
    package = download(f"{GITHUB_RAW}/v{version}/{PACKAGE}.ankiaddon", MAX_PACKAGE_SIZE)
    if hashlib.sha256(package).hexdigest() != checksum:
        raise ValueError("Update checksum did not match")
    validate_package(package, version)
    return Update(version, package)


def check_for_updates_from_dialog(mw, dialog, button, tr):
    button.setEnabled(False)

    def on_done(future):
        if not dialog.isVisible():
            return
        button.setEnabled(True)
        try:
            update = future.result()
        except Exception:
            logger.exception("Could not check for an add-on update")
            showWarning(tr("update_check_failed"), parent=dialog)
            return

        if update is None:
            showInfo(tr("update_current"), parent=dialog)
            return
        if not askUser(tr("update_confirm", version=update.version), parent=dialog, defaultno=True):
            return
        try:
            if not isinstance(mw.addonManager.install(BytesIO(update.package)), InstallOk):
                raise ValueError("Anki rejected the update")
        except Exception:
            logger.exception("Could not install the add-on update")
            showWarning(tr("update_install_failed"), parent=dialog)
            return
        button.setEnabled(False)
        showInfo(tr("update_installed", version=update.version), parent=dialog)

    mw.taskman.with_progress(
        lambda: check_for_update(installed_version()),
        on_done=on_done,
        parent=dialog,
        label=tr("update_checking"),
        uses_collection=False,
    )
