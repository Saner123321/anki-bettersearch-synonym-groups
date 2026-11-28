import re
import unicodedata

from .i18n import WordlistError


ALIAS_SEPARATOR = re.compile(r"[/／]")


def is_han(char):
    return unicodedata.name(char, "").startswith(
        ("CJK UNIFIED IDEOGRAPH", "CJK COMPATIBILITY IDEOGRAPH")
    )


def fuzzy_patterns(alias):
    positions = [i for i, char in enumerate(alias) if is_han(char)]
    if len(positions) < 3:
        return []
    return [alias[:i] + r"\p{Han}" + alias[i + 1 :] for i in positions]


def group_fuzzy_patterns(aliases):
    return list(dict.fromkeys(pattern for alias in aliases for pattern in fuzzy_patterns(alias)))


def regex_query(patterns):
    return '"re:(?:' + "|".join(patterns) + ')"'


def build_query(aliases, fuzzy):
    terms = [f'"{alias}"' if " " in alias else alias for alias in aliases]
    if fuzzy:
        patterns = group_fuzzy_patterns(aliases)
        if patterns:
            terms.append(regex_query(patterns))
    return "(" + " OR ".join(terms) + ")"


def clean_term(term):
    return " ".join(unicodedata.normalize("NFC", term).split())


def split_suffixes(suffix_text):
    if not suffix_text.strip():
        return []
    return list(dict.fromkeys(clean_term(term) for term in ALIAS_SEPARATOR.split(suffix_text)))


def valid_term(term):
    return (
        bool(term)
        and term.casefold() not in {"and", "or"}
        and all(char.isalnum() or char == " " for char in term)
    )


def build_rules(rows):
    groups = []
    rules = {}
    for number, (alias_text, suffix_text, fuzzy) in enumerate(rows, start=1):
        if not alias_text.strip() and not suffix_text.strip():
            continue
        aliases = [clean_term(term) for term in ALIAS_SEPARATOR.split(alias_text)]
        suffixes = split_suffixes(suffix_text)
        if len(set(alias.casefold() for alias in aliases)) < 2:
            raise WordlistError("need_aliases", row=number)
        if not all(valid_term(term) for term in aliases + suffixes):
            raise WordlistError("invalid_term", row=number)
        aliases = list(dict.fromkeys(aliases))
        query = build_query(aliases, fuzzy)
        triggers = {alias.casefold() for alias in aliases}
        triggers.update((alias + suffix).casefold() for alias in aliases for suffix in suffixes)
        overlap = sorted(triggers & rules.keys())
        if overlap:
            raise WordlistError("duplicate_trigger", term=overlap[0])
        rules.update(dict.fromkeys(triggers, query))
        # Older installations can still read and use the first suffix.
        group = {"aliases": aliases, "suffix": suffixes[0] if suffixes else "", "fuzzy": fuzzy}
        if len(suffixes) > 1:
            group["suffixes"] = suffixes
        groups.append(group)
    return groups, rules


def group_rows(groups):
    for group in groups:
        suffix_text = " / ".join(group.get("suffixes", [group["suffix"]]))
        yield " / ".join(group["aliases"]), suffix_text, group["fuzzy"]
