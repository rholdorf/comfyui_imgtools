import { app } from "../../scripts/app.js";

const NODE_NAME = "ResolutionSelectorFromDimensions";
const DISPLAY_WIDGET = "aspect_ratio";

const ASPECT_RATIOS = [
    ["1:1 (Square)", 1, 1],
    ["2:3 (Portrait Photo)", 2, 3],
    ["3:2 (Photo)", 3, 2],
    ["3:4 (Portrait Standard)", 3, 4],
    ["4:3 (Standard)", 4, 3],
    ["9:16 (Portrait Widescreen)", 9, 16],
    ["16:9 (Widescreen)", 16, 9],
    ["21:9 (Ultrawide)", 21, 9],
];

function closestAspectRatio(width, height) {
    if (!width || !height || width <= 0 || height <= 0) return ASPECT_RATIOS[0][0];
    const target = Math.log(width / height);
    let best = ASPECT_RATIOS[0];
    let bestDist = Infinity;
    for (const cand of ASPECT_RATIOS) {
        const d = Math.abs(Math.log(cand[1] / cand[2]) - target);
        if (d < bestDist) { bestDist = d; best = cand; }
    }
    return best[0];
}

app.registerExtension({
    name: "rholdorf.ResolutionSelectorFromDimensions",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated?.apply(this, arguments);

            const box = document.createElement("div");
            box.style.cssText = [
                "box-sizing: border-box",
                "width: 100%",
                "padding: 4px 8px",
                "font: 12px sans-serif",
                "color: #d0d0d0",
                "background: rgba(0,0,0,0.25)",
                "border: 1px solid rgba(255,255,255,0.08)",
                "border-radius: 4px",
                "text-align: center",
            ].join(";");
            box.textContent = "";

            const displayWidget = this.addDOMWidget(DISPLAY_WIDGET, "text", box, {
                serialize: false,
                getValue: () => box.textContent,
                setValue: (v) => { box.textContent = v ?? ""; },
            });
            displayWidget.computeSize = () => [0, 26];

            // Poll on every draw with a value guard. Covers both live edits and
            // workflow reload (configure() writes widget.value without firing
            // the callback, so a hook on the widget callback wouldn't refresh).
            let lastLabel = null;
            const node = this;
            const refresh = () => {
                const w = node.widgets?.find(x => x.name === "width")?.value ?? 0;
                const h = node.widgets?.find(x => x.name === "height")?.value ?? 0;
                const label = closestAspectRatio(w, h);
                if (label !== lastLabel) {
                    lastLabel = label;
                    box.textContent = label;
                }
            };

            const onDrawForeground = this.onDrawForeground;
            this.onDrawForeground = function (ctx) {
                const r = onDrawForeground?.apply(this, arguments);
                refresh();
                return r;
            };

            refresh();

            return ret;
        };
    },
});
