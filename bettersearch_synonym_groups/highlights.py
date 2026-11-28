import json
from pathlib import Path
import sys

from aqt import gui_hooks

from .rules import build_query, group_fuzzy_patterns
from .search import SEARCH_TOKEN, literal_term


SCRIPT = Path(__file__).with_name("highlights.js").read_text(encoding="utf-8")
queries = {}


def set_groups(groups):
    queries.clear()
    for group in groups:
        aliases = group["aliases"]
        fuzzy = group_fuzzy_patterns(aliases)
        for patterns, query in (
            (aliases, build_query(aliases, False)),
            (aliases + fuzzy, build_query(aliases, True)),
        ):
            queries[query] = patterns
            # Anki removes the outer parentheses if the group is the whole query.
            queries[query[1:-1]] = patterns


def search_patterns(search, include_literals=False):
    if search in queries:
        return queries[search]

    patterns = []
    stack = []
    previous = None
    for match in SEARCH_TOKEN.finditer(search):
        token = match.group()
        excluded = previous == "-" or bool(stack and stack[-1][1])
        if token == "(":
            stack.append((match.start(), excluded))
        elif token == ")" and stack:
            start, excluded = stack.pop()
            if not excluded:
                patterns.extend(queries.get(search[start:match.end()], ()))
        elif include_literals and not excluded and (term := literal_term(token)):
            patterns.append(term)
        previous = token
    return list(dict.fromkeys(patterns))


def paint(editor, patterns):
    editor.web.eval(f"({SCRIPT})({json.dumps(patterns)})")


def on_search(context):
    browser = context.browser
    before = getattr(browser, "_synonym_highlight_patterns", ())
    original = (context.addon_metadata or {}).get(__package__)
    after = (
        search_patterns(context.search)
        if original is None
        else search_patterns(original, include_literals=True)
    )
    browser._synonym_highlight_patterns = after
    if before and not after:
        paint(browser.editor, ())


def on_editor_loaded(editor):
    browser = editor.parentWindow
    patterns = getattr(browser, "_synonym_highlight_patterns", ())
    if patterns and getattr(browser, "_highlight_results", True):
        paint(editor, patterns)


def connect():
    gui_hooks.browser_did_search.append(on_search)
    gui_hooks.editor_did_load_note.append(on_editor_loaded)

    legacy = sys.modules.get("225180905.browser")
    if legacy is None:
        return
    original_row_change = legacy.on_browser_did_change_row
    original_toggle = legacy.toggle_search_highlights

    def on_row_change(browser, *args):
        if getattr(browser, "_synonym_highlight_patterns", ()):
            # Qt's single-term find selection would otherwise cover our ranges.
            legacy.clear_highlights(browser.editor.web)
        else:
            original_row_change(browser, *args)

    def toggle(browser, checked):
        original_toggle(browser, checked)
        patterns = getattr(browser, "_synonym_highlight_patterns", ())
        if patterns:
            paint(browser.editor, patterns if checked else ())

    gui_hooks.browser_did_change_row.remove(original_row_change)
    gui_hooks.browser_did_change_row.append(on_row_change)
    legacy.on_browser_did_change_row = on_row_change
    legacy.toggle_search_highlights = toggle
