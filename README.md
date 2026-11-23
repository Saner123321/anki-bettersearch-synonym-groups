# Synonym Groups for BetterSearch

An Anki Desktop companion add-on for finding the same concept under different names, spellings, or transliterations. It extends the existing Browse search box and adds a word-list editor to the [BetterSearch](https://github.com/ijgnd/anki__BetterSearch) menu.

## Install

1. Install [BetterSearch](https://ankiweb.net/shared/info/1052724801) using add-on code `1052724801` and use its newer implementation.
2. [Download the v0.1.0 preview package](https://raw.githubusercontent.com/Saner123321/anki-bettersearch-synonym-groups/v0.1.0/bettersearch_synonym_groups.ankiaddon). In Anki, choose **Tools → Add-ons → Install from file** and select the package.
3. Restart Anki, then open **Browse → BetterSearch → 同义词词表…** (Synonym Groups).

The word-list interface is currently in Chinese. The add-on has been tested on Windows with Anki 26.09.4.

## Use

- Put each group on its own row. Separate equivalent terms with `/` in **同义词** (Synonyms).
- Add optional endings in **可省略的后缀** (Optional suffixes), also separated by `/`. For example, aliases `约当 / 若当 / Jordan` with suffixes `块 / 型` can be found by entering `约当`, `约当块`, or `约当型`.
- Search from the Browse box as usual, with filters such as `deck:LinearAlgebra 约当型`. The add-on expands the configured terms and supports highlighting the matching text in the editor.
- **允许错一字** (Allow one character substitution) lets the search match one different Han character in aliases containing at least three Han characters.

## Share a word list between computers

Install the add-on on each desktop that uses the same Anki collection. On the computer with the word list you want to share, open the editor, enable **随 Anki 同步词表** (Sync word list with Anki), save, and complete Anki's media sync. Sync on the other computer to load the word list. Changes are synced as a single media file, so finish syncing before switching computers to edit it.

The release package ships with one example group. Sync is opt-in and uses the collection's existing Anki sync server. The add-on runs on Anki Desktop.

## Build from source

From the repository root:

```sh
cd bettersearch_synonym_groups
python -m zipfile -c ../bettersearch_synonym_groups.ankiaddon __init__.py config.json highlights.js highlights.py manifest.json rules.py search.py wordlist_sync.py
```
