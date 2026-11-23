import re
import unicodedata


# Keep quoted phrases, escaped characters and field filters as single tokens.
SEARCH_TOKEN = re.compile(r'[-()]|(?:\\.|"(?:\\.|[^"\\])*"|[^\s()"\\])+')


def expand_search(search, rules, expanded_queries):
    if search.strip() in expanded_queries:
        return search

    replacements = []
    groups = []
    for match in SEARCH_TOKEN.finditer(search):
        token = match.group()
        if token == "(":
            groups.append((match.start(), len(replacements)))
        elif token == ")" and groups:
            start, first_replacement = groups.pop()
            if search[start : match.end()] in expanded_queries:
                del replacements[first_replacement:]
        else:
            term = token.removeprefix('"').removesuffix('"')
            key = unicodedata.normalize("NFC", term).casefold()
            if key in rules:
                replacements.append((match.start(), match.end(), rules[key]))

    parts = []
    end = 0
    for start, stop, replacement in replacements:
        parts.extend((search[end:start], replacement))
        end = stop
    parts.append(search[end:])
    return "".join(parts)
