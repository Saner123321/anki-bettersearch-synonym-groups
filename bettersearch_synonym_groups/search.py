import re
import unicodedata

from .rules import group_fuzzy_patterns, regex_query, valid_term


# Keep quoted phrases, escaped characters and field filters as single tokens.
SEARCH_TOKEN = re.compile(r'[-()]|(?:\\.|"(?:\\.|[^"\\])*"|[^\s()"\\])+')

# Only span inline formatting so that content on opposite sides of a line break
# or block boundary is not treated as a single phrase.
INLINE_TAGS = r"(?:</?(?:a|b|big|code|del|em|font|i|ins|mark|s|small|span|strike|strong|sub|sup|u)(?:\s[^<>]*)?>)*"
FUZZY_ATOM = re.compile(r"\\p\{Han\}|.")


def literal_term(token):
    term = token.removeprefix('"').removesuffix('"')
    if len(term) >= 2 and valid_term(term) and any(char.isalpha() for char in term):
        return term
    return None


def inline_fuzzy_queries(groups):
    queries = {}
    for group in groups:
        if group["fuzzy"] and (patterns := group_fuzzy_patterns(group["aliases"])):
            queries[regex_query(patterns)] = regex_query(
                INLINE_TAGS.join(FUZZY_ATOM.findall(pattern)) for pattern in patterns
            )
    return queries


def expand_inline_formatting(search, fuzzy_queries):
    def replace(match):
        token = match.group()
        if token in fuzzy_queries:
            return fuzzy_queries[token]
        if term := literal_term(token):
            inline_query = regex_query([INLINE_TAGS.join(term)])
            return f"({token} OR {inline_query})"
        return token

    return SEARCH_TOKEN.sub(replace, search)


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
