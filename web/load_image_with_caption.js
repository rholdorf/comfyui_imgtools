import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const NODE_NAME = "LoadImageWithCaption";
const IMAGE_WIDGET = "image";
const IMAGE_EXT_RE = /\.(png|jpe?g|webp|gif|bmp)$/i;
const TXT_EXT_RE = /\.txt$/i;

async function uploadOne(file, { overwrite = false } = {}) {
    const form = new FormData();
    form.append("image", file, file.name);
    form.append("type", "input");
    form.append("subfolder", "");
    if (overwrite) form.append("overwrite", "true");
    const resp = await api.fetchApi("/upload/image", { method: "POST", body: form });
    if (resp.status !== 200) {
        const body = await resp.text().catch(() => "");
        throw new Error(`HTTP ${resp.status} ${body}`);
    }
    return await resp.json();
}

function stemOf(name) {
    return name.replace(/\.[^./\\]+$/, "");
}

function makeFileInput() {
    const el = document.createElement("input");
    el.type = "file";
    el.accept = "image/*,.txt,text/plain";
    el.multiple = true;
    el.style.display = "none";
    document.body.appendChild(el);
    return el;
}

app.registerExtension({
    name: "rholdorf.LoadImageWithCaption",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== NODE_NAME) return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            const ret = onNodeCreated?.apply(this, arguments);

            const fileInput = makeFileInput();

            fileInput.addEventListener("change", async () => {
                const files = Array.from(fileInput.files || []);
                fileInput.value = "";
                if (!files.length) return;

                const imageFile = files.find(f => IMAGE_EXT_RE.test(f.name));
                const txtFile = files.find(f => TXT_EXT_RE.test(f.name));
                console.log("[LoadImageWithCaption] picked:",
                    { image: imageFile?.name, txt: txtFile?.name });

                if (!imageFile) {
                    alert("[LoadImageWithCaption] Select an image file (.png/.jpg/.webp).");
                    return;
                }

                let imgResp;
                try {
                    imgResp = await uploadOne(imageFile);
                } catch (err) {
                    console.error("[LoadImageWithCaption] image upload failed:", err);
                    alert(`[LoadImageWithCaption] Image upload failed: ${err.message}`);
                    return;
                }
                const finalImageName = imgResp.name || imageFile.name;
                const finalStem = stemOf(finalImageName);
                console.log("[LoadImageWithCaption] image saved as:", finalImageName);

                if (txtFile) {
                    const txtName = `${finalStem}.txt`;
                    try {
                        const renamed = new File([txtFile], txtName, {
                            type: txtFile.type || "text/plain",
                        });
                        // overwrite=true so the .txt always ends up at the matching stem,
                        // even if a stale unrelated <stem>.txt already exists in input/.
                        const txtResp = await uploadOne(renamed, { overwrite: true });
                        console.log("[LoadImageWithCaption] caption saved as:", txtResp.name);
                    } catch (err) {
                        console.error("[LoadImageWithCaption] caption upload failed:", err);
                        alert(`[LoadImageWithCaption] Caption upload failed: ${err.message}`);
                    }
                } else {
                    console.log("[LoadImageWithCaption] no .txt in selection — caption will be empty");
                }

                const imageWidget = this.widgets?.find(w => w.name === IMAGE_WIDGET);
                if (imageWidget) {
                    const values = imageWidget.options?.values;
                    if (Array.isArray(values) && !values.includes(finalImageName)) {
                        values.push(finalImageName);
                        values.sort();
                    }
                    imageWidget.value = finalImageName;
                    imageWidget.callback?.(finalImageName);
                    app.graph.setDirtyCanvas(true, true);
                }
            });

            const btn = this.addWidget("button", "upload pair (.png + .txt)", null, () => {
                fileInput.click();
            });
            btn.serialize = false;

            const onRemoved = this.onRemoved;
            this.onRemoved = function () {
                fileInput.remove();
                return onRemoved?.apply(this, arguments);
            };

            return ret;
        };
    },
});
