LANGUAGE_CHOICES = (
    ("auto", "Follow Anki / 跟随 Anki"),
    ("zh-CN", "简体中文"),
    ("en", "English"),
)

TEXT = {
    "en": {
        "menu": "Synonym Groups…",
        "title": "BetterSearch Synonym Groups",
        "ui_language": "Language",
        "search": "Find a synonym or suffix",
        "help": "Use / to separate synonyms in each row. Typo matching allows one Han character to differ in terms containing at least three Han characters.",
        "bulk_typos": "Allow one typo in all groups",
        "bulk_tip": "Applies to the whole word list, including groups hidden by the filter.",
        "sync": "Sync word list with Anki",
        "sync_tip": "Enable and save to include the word list in media sync for this profile.",
        "sync_enabled": "This word list syncs with Anki media",
        "sync_enabled_tip": "Media sync is enabled for this word list in the current profile.",
        "synonyms": "Synonyms",
        "suffixes": "Optional suffixes",
        "typos": "Allow one typo",
        "suffix_tip": "Separate endings with /. Use a synonym by itself or with any of its configured endings.",
        "count": "{visible} of {total} groups",
        "add": "Add group",
        "remove": "Delete selected groups",
        "save": "Save",
        "cancel": "Cancel",
        "update_check": "Check for updates",
        "update_checking": "Checking GitHub for updates…",
        "update_current": "The installed add-on is up to date.",
        "update_confirm": "Version {version} is ready to install from GitHub. Install it now?",
        "update_installed": "Installed version {version}. Save any word-list edits and restart Anki to use it.",
        "update_check_failed": "Could not check or download the update from GitHub. Please try again.",
        "update_install_failed": "Anki could not install the update. Please try again.",
        "require_bettersearch": "Enable the newer version of BetterSearch (1052724801), then restart Anki.",
        "read_failed": "The synced word list could not be read. Finish media sync, then reopen Synonym Groups.",
        "save_failed": "Unable to save the synonym word list. Please try again.",
        "language_save_failed": "Unable to save the interface language. Please try again.",
        "profile_changed": "The Anki profile changed. Reopen Synonym Groups before editing.",
        "wordlist_changed": "The word list changed during editing. Reopen Synonym Groups to edit the latest version.",
        "sync_busy": "Media sync is running. Wait for it to finish before saving the word list.",
        "register_failed": "Anki could not register the word list for media sync. Please try saving again.",
        "need_aliases": "Row {row} needs at least two different synonyms separated by /.",
        "invalid_term": "Row {row} can contain letters, numbers, and spaces. Separate alternatives with /.",
        "duplicate_trigger": "“{term}” appears in more than one group. Merge or edit the groups.",
    },
    "zh-CN": {
        "menu": "同义词词表…",
        "title": "BetterSearch 同义词词表",
        "ui_language": "界面语言",
        "search": "搜索词表（同义词或后缀）",
        "help": "每行一组，同义词用 / 分隔。开启错字匹配后，含至少三个汉字的词允许其中一个字写错。",
        "bulk_typos": "全部允许错一字",
        "bulk_tip": "作用于整个词表，包括搜索时隐藏的规则。",
        "sync": "随 Anki 同步词表",
        "sync_tip": "勾选并保存后，词表会随当前资料的 Anki 媒体同步。",
        "sync_enabled": "词表随 Anki 媒体同步",
        "sync_enabled_tip": "当前资料已启用词表的 Anki 媒体同步。",
        "synonyms": "同义词",
        "suffixes": "可省略的后缀",
        "typos": "允许错一字",
        "suffix_tip": "多个后缀用 / 分隔。搜索时可单独输入同义词，也可加上任一已设置的后缀。",
        "count": "显示 {visible} / {total} 组",
        "add": "添加一组",
        "remove": "删除选中组",
        "save": "保存",
        "cancel": "取消",
        "update_check": "检查更新",
        "update_checking": "正在通过 GitHub 检查更新…",
        "update_current": "本机安装的插件已是最新版。",
        "update_confirm": "GitHub 上有新版本 {version}。现在安装吗？",
        "update_installed": "已安装 {version}。请保存词表编辑，再重启 Anki 使更新生效。",
        "update_check_failed": "无法从 GitHub 检查或下载更新，请重试。",
        "update_install_failed": "Anki 无法安装更新，请重试。",
        "require_bettersearch": "请启用新版 BetterSearch（1052724801），然后重启 Anki。",
        "read_failed": "无法读取已同步的词表。请确认媒体同步已完成，再打开词表。",
        "save_failed": "无法保存词表，请重试。",
        "language_save_failed": "无法保存界面语言，请重试。",
        "profile_changed": "Anki 资料已切换。请重新打开词表。",
        "wordlist_changed": "词表在编辑期间已更新。请重新打开词表，再编辑最新内容。",
        "sync_busy": "媒体正在同步。请等待同步完成后再保存词表。",
        "register_failed": "Anki 未能登记词表用于媒体同步，请重试保存。",
        "need_aliases": "第 {row} 行至少需要两个不同的写法，用 / 分隔。",
        "invalid_term": "第 {row} 行请使用文字、数字和空格。不同写法之间用 / 分隔。",
        "duplicate_trigger": "「{term}」同时出现在多组里，请合并或修改。",
    },
}


def resolve_language(setting, anki_language):
    if isinstance(setting, str) and setting in TEXT:
        return setting
    base = (anki_language or "").replace("_", "-").split("-", 1)[0].lower()
    return "zh-CN" if base == "zh" else "en"


def translate(language, key, **values):
    return TEXT[language][key].format(**values)


class WordlistError(ValueError):
    def __init__(self, key, **values):
        self.key = key
        self.values = values
        super().__init__(self.localized("en"))

    def localized(self, language):
        return translate(language, self.key, **self.values)
