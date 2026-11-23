# Synonym Groups for BetterSearch

An Anki Desktop companion add-on for finding the same concept under different names, spellings, or transliterations. It extends the existing Browse search box and adds a word-list editor to the [BetterSearch](https://github.com/ijgnd/anki__BetterSearch) menu.

## Install

1. Install [BetterSearch](https://ankiweb.net/shared/info/1052724801) using add-on code `1052724801` and use its newer implementation.
2. [Download the v0.1.4 preview package](https://github.com/Saner123321/anki-bettersearch-synonym-groups/blob/v0.1.4/bettersearch_synonym_groups.ankiaddon). Use the download button on GitHub, then choose **Tools → Add-ons → Install from file** in Anki and select the package.
3. Restart Anki, then open **Browse → BetterSearch → Synonym Groups…** (同义词词表…).

The interface follows Anki's language by default, using Simplified Chinese for Chinese locales and English otherwise. The **Language** (界面语言) selector changes the interface immediately and remembers your choice on this computer. The add-on has been tested on Windows with Anki 26.09.4.

From v0.1.2 onward, **Check for updates** (检查更新) in the word-list window can install newer versions from this GitHub repository. Confirm the update when prompted, then restart Anki. On older versions, install the current package from the download link once to get the update button.

Since v0.1.4, the updater also checks GitHub's Contents API if the raw download fails. If your older updater cannot connect, install the current package using the link above.

## Use

- Put each group on its own row. Separate equivalent terms with `/` in **Synonyms**.
- Add endings in **Optional suffixes**, also separated by `/`. For example, aliases `约当 / 若当 / Jordan` with suffixes `块 / 型` can be found by entering `约当`, `约当块`, or `约当型`.
- Search from the Browse box as usual, with filters such as `deck:LinearAlgebra 约当型`. The add-on expands the configured terms and supports highlighting the matching text in the editor.
- **Allow one typo** lets the search match one different Han character in aliases containing at least three Han characters.

## Share a word list between computers

Install the add-on on each desktop that uses the same Anki collection. On the computer with the word list you want to share, open the editor, enable **Sync word list with Anki**, save, and complete Anki's media sync. Sync on the other computer to load the word list. Changes are synced as a single media file, so finish syncing before switching computers to edit it.

The release package ships with one example group. Sync is opt-in and uses the collection's existing Anki sync server. The add-on runs on Anki Desktop.

## Build from source

From the repository root:

```sh
python build_release.py
```

This creates the installer and updates `update.json` with its version and SHA-256 checksum. For a new preview, set `human_version` in `bettersearch_synonym_groups/manifest.json` before building. Publish the matching `v<version>` tag and the updated main branch together so the tagged installer is available when the updater sees its version.
