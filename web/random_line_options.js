import { app } from "../../scripts/app.js";

const NODE_NAME = "RandomLineConcatenator";
const SOURCE_WIDGET = "random_choice";
const EDITOR_WIDGET = "options_editor";

function parseValue(raw) {
    const s = String(raw ?? "").trim();
    if (!s) return [];
    if (s.startsWith("[")) {
        try {
            const data = JSON.parse(s);
            if (Array.isArray(data)) {
                return data
                    .filter(e => e && typeof e === "object")
                    .map(e => ({ enabled: e.enabled !== false, text: String(e.text ?? "") }));
            }
        } catch (_) {}
    }
    // Legacy: one entry per non-empty line.
    return s.split("\n")
        .map(l => l.trim())
        .filter(Boolean)
        .map(text => ({ enabled: true, text }));
}

function makeRow(entry, onEdit, onDelete) {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:6px;padding:1px 0;";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = entry.enabled;
    cb.title = "Include this option in the random pool";
    cb.style.cssText = "flex:0 0 auto;cursor:pointer;";

    const txt = document.createElement("input");
    txt.type = "text";
    txt.value = entry.text;
    txt.placeholder = "option text";
    txt.style.cssText =
        "flex:1 1 auto;min-width:0;background:#1a1a1a;color:#ddd;" +
        "border:1px solid #444;border-radius:3px;padding:2px 6px;font-size:12px;";

    const del = document.createElement("button");
    del.type = "button";
    del.textContent = "×";
    del.title = "Remove this option";
    del.style.cssText =
        "flex:0 0 auto;width:22px;height:22px;line-height:1;cursor:pointer;" +
        "background:#2a2a2a;color:#aaa;border:1px solid #444;border-radius:3px;";

    cb.addEventListener("change", () => onEdit({ enabled: cb.checked, text: txt.value }));
    txt.addEventListener("input", () => onEdit({ enabled: cb.checked, text: txt.value }));
    del.addEventListener("click", onDelete);

    row.append(cb, txt, del);
    return row;
}

function rebuild(node, container, sourceWidget) {
    const entries = parseValue(sourceWidget.value);

    // Normalize back to JSON so the on-disk format converges to the new shape.
    const serialized = JSON.stringify(entries);
    if (sourceWidget.value !== serialized) sourceWidget.value = serialized;

    container.innerHTML = "";

    entries.forEach((entry, idx) => {
        const row = makeRow(
            entry,
            (next) => {
                entries[idx] = next;
                sourceWidget.value = JSON.stringify(entries);
            },
            () => {
                entries.splice(idx, 1);
                sourceWidget.value = JSON.stringify(entries);
                rebuild(node, container, sourceWidget);
            },
        );
        container.appendChild(row);
    });

    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.textContent = "+ Add entry";
    addBtn.style.cssText =
        "margin-top:6px;padding:4px 8px;cursor:pointer;align-self:flex-start;" +
        "background:#2a2a2a;color:#ddd;border:1px solid #555;border-radius:3px;font-size:12px;";
    addBtn.addEventListener("click", () => {
        entries.push({ enabled: true, text: "" });
        sourceWidget.value = JSON.stringify(entries);
        rebuild(node, container, sourceWidget);
    });
    container.appendChild(addBtn);
}

function installEditor(node) {
    const sourceWidget = node.widgets?.find(w => w.name === SOURCE_WIDGET);
    if (!sourceWidget) return;
    if (node.widgets.some(w => w.name === EDITOR_WIDGET)) return; // already installed

    // Hide the underlying STRING widget without removing it. It still holds the
    // serialized value used by widgets_values save/load.
    sourceWidget.type = "hidden";
    sourceWidget.computeSize = () => [0, -4];

    const container = document.createElement("div");
    container.style.cssText =
        "display:flex;flex-direction:column;gap:2px;padding:4px;width:100%;box-sizing:border-box;";

    const editor = node.addDOMWidget(EDITOR_WIDGET, "rholdorf-options", container, {
        hideOnZoom: false,
    });
    editor.serialize = false; // value lives in the hidden source widget
    editor.options = editor.options || {};
    editor.options.minNodeSize = [360, 120];

    rebuild(node, container, sourceWidget);
}

app.registerExtension({
    name: "rholdorf.RandomLineOptions",

    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated?.apply(this, arguments);
            installEditor(this);
            return ret;
        };

        const onConfigure = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (info) {
            const ret = onConfigure?.apply(this, arguments);
            // After configure restores widget values, rebuild the editor DOM
            // from the (possibly legacy) random_choice value.
            const node = this;
            queueMicrotask(() => {
                const src = node.widgets?.find(w => w.name === SOURCE_WIDGET);
                const editor = node.widgets?.find(w => w.name === EDITOR_WIDGET);
                if (src && editor?.element) rebuild(node, editor.element, src);
            });
            return ret;
        };
    },
});
