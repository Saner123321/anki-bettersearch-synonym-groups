import logging
import sys
import unicodedata

from aqt import gui_hooks, mw
from aqt.qt import (
    QAbstractItemView,
    QCheckBox,
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
from .rules import ALIAS_SEPARATOR, build_rules, clean_term, group_rows, split_suffixes
from .search import expand_search
from .wordlist_sync import decode_groups, read_wordlist, wordlist_path, write_wordlist


BETTERSEARCH_MODULE = "1052724801.new.onTextChange"
logger = logging.getLogger(__name__)
rules = {}
typing_prefixes = set()


class RuleFilter(QLineEdit):
    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            event.accept()
            return
        super().keyPressEvent(event)


def config():
    return mw.addonManager.getConfig(__name__) or {}


def activate_groups(groups, replacement_rules):
    global rules, typing_prefixes
    rules = replacement_rules
    typing_prefixes = {
        term[:length]
        for term in rules
        for length in range(1, len(term))
        if term[:length] in rules
    }
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
    context.search = expand_search(context.search, rules, highlights.queries)


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
            action.menu().addAction("同义词词表…", lambda: edit_groups(browser))
            break


def edit_groups(parent=None):
    if BETTERSEARCH_MODULE not in sys.modules:
        showWarning("请启用新版 BetterSearch（1052724801），然后重启 Anki。", parent=parent)
        return

    current_config = config()
    collection = getattr(mw, "col", None)
    sync_path = wordlist_path(collection)
    try:
        synced = read_wordlist(sync_path)
        current_groups = decode_groups(synced) if synced is not None else current_config.get("groups", [])
    except (OSError, ValueError):
        showWarning("无法读取已同步的词表。请确认媒体同步已完成，再打开词表。", parent=parent)
        return

    dialog = QDialog(parent or mw)
    dialog.setWindowTitle("BetterSearch 同义词词表")
    dialog.resize(760, 360)
    layout = QVBoxLayout(dialog)

    search_bar = QHBoxLayout()
    rule_filter = RuleFilter(dialog)
    rule_filter.setPlaceholderText("搜索词表（同义词或后缀）")
    rule_filter.setClearButtonEnabled(True)
    search_bar.addWidget(rule_filter, 1)
    result_count = QLabel(dialog)
    search_bar.addWidget(result_count)
    layout.addLayout(search_bar)

    help_text = QLabel(
        "每行一组，用 / 分隔。搜索任意写法即可。勾选后，三个汉字及以上的词允许其中一个汉字写错。"
    )
    help_text.setWordWrap(True)
    layout.addWidget(help_text)

    allow_all_typos = QCheckBox("全部允许错一字", dialog)
    allow_all_typos.setTristate(True)
    allow_all_typos.setToolTip("作用于整个词表，包括搜索时隐藏的规则。")
    layout.addWidget(allow_all_typos)

    enable_sync = QCheckBox("随 Anki 同步词表", dialog)
    enable_sync.setToolTip("勾选并保存后，词表会随当前资料的 Anki 媒体同步。")
    if synced is not None:
        layout.addWidget(QLabel("词表随 Anki 媒体同步", dialog))
    elif sync_path is not None:
        layout.addWidget(enable_sync)

    table = QTableWidget(0, 3, dialog)
    table.setHorizontalHeaderLabels(["同义词", "可省略的后缀", "允许错一字"])
    table.horizontalHeaderItem(1).setToolTip(
        "多个后缀用 / 分隔。例如填「块 / 型」，输入「约当」、「约当块」或「约当型」都能触发。"
    )
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
        result_count.setText(f"显示 {visible_count} / {table.rowCount()} 组")

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
    update_filter()
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
                raise ValueError("Anki 资料已切换。请重新打开词表。")
            if sync_path is not None and (synced is not None or enable_sync.isChecked()):
                write_wordlist(collection, groups, synced)
            else:
                if read_wordlist(sync_path) is not None:
                    raise ValueError("词表在编辑期间已同步更新。请退出后重新打开词表。")
                current_config["groups"] = groups
                mw.addonManager.writeConfig(__name__, current_config)
        except (OSError, ValueError) as error:
            showWarning(str(error), parent=dialog)
            return
        activate_groups(groups, updated_rules)
        dialog.accept()

    actions = QHBoxLayout()
    add = QPushButton("添加一组")
    add.clicked.connect(add_row)
    add.setAutoDefault(False)
    actions.addWidget(add)
    remove = QPushButton("删除选中组")
    remove.clicked.connect(remove_rows)
    remove.setAutoDefault(False)
    actions.addWidget(remove)
    actions.addStretch()
    layout.addLayout(actions)

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
    )
    buttons.accepted.connect(save)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)
    rule_filter.setFocus()
    dialog.exec()


load_rules(getattr(mw, "col", None))
gui_hooks.main_window_did_init.append(connect_to_bettersearch)
gui_hooks.collection_did_load.append(load_rules)
gui_hooks.media_sync_did_start_or_stop.append(after_media_sync)
mw.addonManager.setConfigAction(__name__, edit_groups)
