import json
from pathlib import Path
from tempfile import TemporaryDirectory


FILENAME = "_bettersearch_synonym_groups.json"


def wordlist_path(col):
    if col is None:
        return None
    return Path(col.media.dir()) / FILENAME


def read_wordlist(path):
    if path is None:
        return None
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


def decode_groups(data):
    document = json.loads(data)
    if not isinstance(document, dict) or document.get("version") != 1:
        raise ValueError("Unsupported word list format")
    groups = document.get("groups")
    if not isinstance(groups, list):
        raise ValueError("Missing word list")
    for group in groups:
        if (
            not isinstance(group, dict)
            or not isinstance(group.get("aliases"), list)
            or not all(isinstance(alias, str) for alias in group["aliases"])
            or not isinstance(group.get("suffix"), str)
            or not isinstance(group.get("fuzzy"), bool)
        ):
            raise ValueError("Invalid synonym group")
        suffixes = group.get("suffixes", [])
        if not isinstance(suffixes, list) or not all(isinstance(suffix, str) for suffix in suffixes):
            raise ValueError("Invalid optional suffixes")
    return groups


def write_wordlist(col, groups, previous):
    path = wordlist_path(col)
    if read_wordlist(path) != previous:
        raise ValueError("词表在编辑期间已同步更新。请退出后重新打开词表，再编辑最新内容。")
    if previous is not None and decode_groups(previous) == groups:
        return
    if col.media_sync_status().active:
        raise ValueError("媒体正在同步。请等待同步完成后再保存词表。")

    data = json.dumps({"version": 1, "groups": groups}, ensure_ascii=False, indent=2)
    payload = (data + "\n").encode("utf-8")
    with TemporaryDirectory(dir=path.parent.parent, prefix="bettersearch-wordlist-") as folder:
        staged = Path(folder) / path.name
        staged.write_bytes(payload)
        if read_wordlist(path) != previous:
            raise ValueError("词表在编辑期间已同步更新。请退出后重新打开词表，再编辑最新内容。")
        staged.replace(path)
        try:
            # Register the new checksum explicitly. Anki's filesystem scan can
            # miss two file replacements within the same second.
            col.media.write_data(path.name, payload)
        except Exception as error:
            if read_wordlist(path) == payload:
                if previous is None:
                    path.unlink()
                else:
                    staged.write_bytes(previous)
                    staged.replace(path)
            raise OSError("Anki 未能登记词表用于媒体同步，请重试保存。") from error
