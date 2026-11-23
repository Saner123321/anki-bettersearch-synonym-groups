function (patterns) {
    const name = "bettersearch-synonyms";
    if (!window.CSS?.highlights) {
        return;
    }

    const highlight = new Highlight();
    const han = "\\p{Han}";
    const width = (pattern) => pattern.replaceAll(han, ".").length;
    const ordered = [...patterns]
        .sort((left, right) => width(right) - width(left))
        .map((pattern) => pattern.replaceAll(han, "\\p{Script=Han}"));
    // The lookahead finds matches at overlapping offsets, too.
    const matcher = new RegExp(`(?=(${ordered.join("|")}))`, "giu");
    const blocks = new Set(["BR", "DIV", "P", "LI", "TD", "TH", "HR", "PRE"]);

    function paintField(field) {
        const pieces = [];
        let text = "";

        function collect(node) {
            if (node.nodeType === Node.TEXT_NODE) {
                const start = text.length;
                text += node.data;
                if (node.data.length) {
                    pieces.push({ node, start, end: text.length });
                }
                return;
            }
            if (["SCRIPT", "STYLE", "TEMPLATE"].includes(node.nodeName) || node.hidden) {
                return;
            }
            const block = blocks.has(node.nodeName);
            if (block && text && !text.endsWith("\n")) {
                text += "\n";
            }
            for (const child of node.childNodes) {
                collect(child);
            }
            if (block && text && !text.endsWith("\n")) {
                text += "\n";
            }
        }

        collect(field);
        for (const match of text.matchAll(matcher)) {
            const start = match.index;
            const end = start + match[1].length;
            const first = pieces.find((piece) => piece.start <= start && start < piece.end);
            const last = pieces.find((piece) => piece.start < end && end <= piece.end);
            if (first && last) {
                const range = new Range();
                range.setStart(first.node, start - first.start);
                range.setEnd(last.node, end - last.start);
                highlight.add(range);
            }
        }
    }

    function visit(root) {
        const fields = root.querySelectorAll('anki-editable[contenteditable="true"]');
        if (fields.length && !root.querySelector("style[data-bettersearch-synonyms]")) {
            const style = document.createElement("style");
            style.setAttribute("data-bettersearch-synonyms", "");
            style.textContent = `::highlight(${name}) { background-color: #ffe26b; color: #251900; }`;
            (root === document ? document.head : root).append(style);
        }
        for (const field of fields) {
            paintField(field);
        }
        for (const element of root.querySelectorAll("*")) {
            if (element.shadowRoot) {
                visit(element.shadowRoot);
            }
        }
    }

    // Anki may finish attaching the editable fields just after its Python hook.
    requestAnimationFrame(() => {
        CSS.highlights.delete(name);
        if (!patterns.length) {
            return;
        }
        visit(document);
        CSS.highlights.set(name, highlight);
    });
}
