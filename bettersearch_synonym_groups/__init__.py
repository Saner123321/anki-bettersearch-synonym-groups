import logging
import sys
import unicodedata

from anki import lang as anki_lang
from aqt import gui_hooks, mw
from aqt.qt import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSignalBlocker,
    QTableWidget,
    QTableWidgetItem,
    Qt,
    QVBoxLayout,
)
from aqt.utils import showWarning

from . import highlights
from .i18n import LANGUAGE_CHOICES, WordlistError, resolve_language, translate
from .rules import ALIAS_SEPARATOR, build_rules, clean_term, group_rows, split_suffixes
from .search import expand_inline_formatting, expand_search, inline_fuzzy_queries
from .updater import PACKAGE, check_for_updates_from_dialog
from .wordlist_sync import decode_groups, read_wordlist, wordlist_path, write_wordlist


BETTERSEARCH_MODULE = "1052724801.new.onTextChange"
logger = logging.getLogger(__name__)
rules = {}
typing_prefixes = set()
formatted_fuzzy_queries = {}


class RuleFilter(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            return
        super().keyPressEvent(event)


def config():
    return mw.addonManager.getConfig(__name__) or {}


def language_for(settings):
    return resolve_language(settings.get("language", "auto"), anki_lang.current_lang)


def activate_groups(groups, replacement_rules):
    global rules, typing_prefixes, formatted_fuzzy_queries
    rules = replacement_rules
    typing_prefixes = {
        term[:length]
        for term in rules
        for length in range(1, len(term))
        if term[:length] in rules
    }
    formatted_fuzzy_queries = inline_fuzzy_queries(groups)
    highlights.set_groups(groups)


def load_rules(col):
    try:
        saved = read_wordlist(wordlist_path(col))
        if saved is not None:
            activate_groups(*build_rules(group_rows(decode_groups(saved))))
            return
    except (OSError, KeyError, TypeError, ValueError):
        logger.warning("Could not load the synced synonym word list")

    try:
        activate_groups(*build_rules(group_rows(config().get("groups", []))))
    except (KeyError, TypeError, ValueError):
        logger.warning("Could not load the local synonym word list")
        activate_groups([], {})


def after_media_sync(running):
    if not running:
        load_rules(getattr(mw, "col", None))


def expand_browser_search(context):
    expanded = expand_search(context.search, rules, highlights.queries)
    context.search = expand_inline_formatting(expanded, formatted_fuzzy_queries)
    if context.search != expanded:
        if context.addon_metadata is None:
            context.addon_metadata = {}
        context.addon_metadata[__name__] = expanded


def connect_to_bettersearch():
    module = sys.modules.get(BETTERSEARCH_MODULE)
    if module is None:
        return
    original = module.regex_replacements

    def replace(before, after):
        if not after:
            key = unicodedata.normalize("NFC", before).casefold()
            if key in typing_prefixes:
                # Expand the shorter form on Enter if the user stops here.
                return None
            query = rules.get(key)
            if query is not None:
                return query, len(query), False
        return original(before, after)

    module.regex_replacements = replace
    gui_hooks.browser_menus_did_init.append(add_browser_menu)
    gui_hooks.browser_will_search.append(expand_browser_search)
    highlights.connect()


def add_browser_menu(browser):
    for action in browser.menuBar().actions():
        if action.text().replace("&", "") == "BetterSearch" and action.menu():
            menu = action.menu()
            entry = menu.addAction(translate(language_for(config()), "menu"), lambda: edit_groups(browser))
            menu.aboutToShow.connect(lambda: entry.setText(translate(language_for(config()), "menu")))
            break


def edit_groups(parent=None):
    current_config = config()
    language = language_for(current_config)

    def tr(key, **values):
        return translate(language, key, **values)

    if BETTERSEARCH_MODULE not in sys.modules:
        showWarning(tr("require_bettersearch"), parent=parent)
        return

    collection = getattr(mw, "col", None)
    sync_path = wordlist_path(collection)
    try:
        synced = read_wordlist(sync_path)
        current_groups = decode_groups(synced) if synced is not None else current_config.get("groups", [])
    except (OSError, ValueError):
        showWarning(tr("read_failed"), parent=parent)
        return

    dialog = QDialog(parent or mw)
    dialog.resize(760, 360)
    layout = QVBoxLayout(dialog)

    search_bar = QHBoxLayout()
    rule_filter = RuleFilter(dialog)
    rule_filter.setClearButtonEnabled(True)
    search_bar.addWidget(rule_filter, 1)
    result_count = QLabel(dialog)
    search_bar.addWidget(result_count)
    layout.addLayout(search_bar)

    help_text = QLabel(dialog)
    help_text.setWordWrap(True)
    layout.addWidget(help_text)

    allow_all_typos = QCheckBox(dialog)
    allow_all_typos.setTristate(True)
    layout.addWidget(allow_all_typos)

    enable_sync = QCheckBox(dialog)
    layout.addWidget(enable_sync)
    enable_sync.setVisible(sync_path is not None)
    enable_sync.setChecked(synced is not None)
    enable_sync.setEnabled(synced is None)

    table = QTableWidget(0, 3, dialog)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
    layout.addWidget(table)

    def update_filter():
        query = clean_term(rule_filter.text()).casefold()
        visible_count = 0
        for row in range(table.rowCount()):
            visible = True
            if query:
                aliases = clean_term(table.item(row, 0).text()).casefold()
                suffixes = split_suffixes(table.item(row, 1).text().casefold())
                full_terms = (
                    alias.strip() + suffix
                    for alias in ALIAS_SEPARATOR.split(aliases)
                    for suffix in suffixes
                )
                visible = query in aliases or any(query in term for term in (*suffixes, *full_terms))
            table.setRowHidden(row, not visible)
            visible_count += visible
        result_count.setText(tr("count", visible=visible_count, total=table.rowCount()))

    def on_filter_changed():
        table.clearSelection()
        update_filter()

    def update_bulk_state():
        total = table.rowCount()
        checked = sum(
            table.item(row, 2).checkState() == Qt.CheckState.Checked
            for row in range(total)
        )
        if checked == 0:
            state = Qt.CheckState.Unchecked
        elif checked == total:
            state = Qt.CheckState.Checked
        else:
            state = Qt.CheckState.PartiallyChecked
        allow_all_typos.setCheckState(state)
        allow_all_typos.setEnabled(total > 0)

    def set_all_typos(enabled):
        state = Qt.CheckState.Checked if enabled else Qt.CheckState.Unchecked
        with QSignalBlocker(table):
            for row in range(table.rowCount()):
                table.item(row, 2).setCheckState(state)
        update_bulk_state()

    def on_item_changed(item):
        if item.column() == 2:
            update_bulk_state()
        else:
            update_filter()

    def append_row(aliases="", suffix="", fuzzy=True):
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(aliases))
        table.setItem(row, 1, QTableWidgetItem(suffix))
        allow_typo = QTableWidgetItem()
        allow_typo.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
        allow_typo.setCheckState(Qt.CheckState.Checked if fuzzy else Qt.CheckState.Unchecked)
        table.setItem(row, 2, allow_typo)
        return row

    for row in group_rows(current_groups):
        append_row(*row)
    update_bulk_state()
    rule_filter.textChanged.connect(on_filter_changed)
    allow_all_typos.clicked.connect(set_all_typos)
    table.itemChanged.connect(on_item_changed)

    def add_row():
        rule_filter.clear()
        row = append_row()
        table.setCurrentCell(row, 0)
        table.editItem(table.item(row, 0))

    def remove_rows():
        selected_rows = [
            index.row()
            for index in table.selectionModel().selectedRows()
            if not table.isRowHidden(index.row())
        ]
        for row in sorted(selected_rows, reverse=True):
            table.removeRow(row)
        update_filter()
        update_bulk_state()

    def save():
        buttons.button(QDialogButtonBox.StandardButton.Save).setFocus()
        rows = [
            (
                table.item(row, 0).text(),
                table.item(row, 1).text(),
                table.item(row, 2).checkState() == Qt.CheckState.Checked,
            )
            for row in range(table.rowCount())
        ]
        try:
            groups, updated_rules = build_rules(rows)
            if wordlist_path(getattr(mw, "col", None)) != sync_path:
                raise WordlistError("profile_changed")
            if sync_path is not None and (synced is not None or enable_sync.isChecked()):
                write_wordlist(collection, groups, synced)
            else:
                if read_wordlist(sync_path) is not None:
                    raise WordlistError("wordlist_changed")
                updated_config = config()
                updated_config["groups"] = groups
                mw.addonManager.writeConfig(__name__, updated_config)
        except WordlistError as error:
            showWarning(error.localized(language), parent=dialog)
            return
        except (OSError, ValueError):
            logger.warning("Could not save the synonym word list")
            showWarning(tr("save_failed"), parent=dialog)
            return
        activate_groups(groups, updated_rules)
        dialog.accept()

    actions = QHBoxLayout()
    add = QPushButton(dialog)
    add.clicked.connect(add_row)
    add.setAutoDefault(False)
    actions.addWidget(add)
    remove = QPushButton(dialog)
    remove.clicked.connect(remove_rows)
    remove.setAutoDefault(False)
    actions.addWidget(remove)
    actions.addStretch()

    update = QPushButton(dialog)
    update.setAutoDefault(False)
    actions.addWidget(update)
    update.setVisible(__package__ == PACKAGE)
    update.clicked.connect(lambda: check_for_updates_from_dialog(mw, dialog, update, tr))

    language_label = QLabel(dialog)
    language_choice = QComboBox(dialog)
    for code, label in LANGUAGE_CHOICES:
        language_choice.addItem(label, code)
    language_choice.setCurrentIndex(max(0, language_choice.findData(current_config.get("language", "auto"))))
    language_label.setBuddy(language_choice)
    actions.addWidget(language_label)
    actions.addWidget(language_choice)
    layout.addLayout(actions)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(save)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    def retranslate():
        dialog.setWindowTitle(tr("title"))
        rule_filter.setPlaceholderText(tr("search"))
        help_text.setText(tr("help"))
        allow_all_typos.setText(tr("bulk_typos"))
        allow_all_typos.setToolTip(tr("bulk_tip"))
        enable_sync.setText(tr("sync" if synced is None else "sync_enabled"))
        enable_sync.setToolTip(tr("sync_tip" if synced is None else "sync_enabled_tip"))
        table.setHorizontalHeaderLabels([tr("synonyms"), tr("suffixes"), tr("typos")])
        table.horizontalHeaderItem(1).setToolTip(tr("suffix_tip"))
        add.setText(tr("add"))
        remove.setText(tr("remove"))
        update.setText(tr("update_check"))
        language_label.setText(tr("ui_language"))
        language_choice.setAccessibleName(tr("ui_language"))
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(tr("save"))
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        update_filter()

    def change_language():
        nonlocal language
        prefs = config()
        previous = prefs.get("language", "auto")
        prefs["language"] = language_choice.currentData()
        try:
            mw.addonManager.writeConfig(__name__, prefs)
        except OSError:
            with QSignalBlocker(language_choice):
                language_choice.setCurrentIndex(max(0, language_choice.findData(previous)))
            showWarning(tr("language_save_failed"), parent=dialog)
            return
        language = language_for(prefs)
        retranslate()

    language_choice.currentIndexChanged.connect(change_language)
    retranslate()
    rule_filter.setFocus()
    dialog.exec()


load_rules(getattr(mw, "col", None))
gui_hooks.main_window_did_init.append(connect_to_bettersearch)
gui_hooks.collection_did_load.append(load_rules)
gui_hooks.media_sync_did_start_or_stop.append(after_media_sync)
mw.addonManager.setConfigAction(__name__, edit_groups)
