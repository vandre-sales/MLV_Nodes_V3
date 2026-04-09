// MLV_Nodes_V3/web/js/mlv_lora_stack.js
// Frontend extension — controla visibilidade dinâmica de slots baseado em num_loras
// Usa widget.hidden (Vue frontend v1.42+) + fallback widget.type (LiteGraph legacy)
// Licença: Proprietário — Meliva Online © 2026

import { app } from "../../scripts/app.js";

const MAX_LORAS = 8;
const NODE_CLASS = "MLV_LoraStack_V3";
const HIDDEN_TYPE = "mlvHidden";

const origProps = {};

function getWidget(node, name) {
    return node.widgets?.find(w => w.name === name);
}

function doesInputWithNameExist(node, name) {
    return node.inputs?.some(input => input.name === name) ?? false;
}

function toggleWidget(node, widget, show) {
    if (!widget || doesInputWithNameExist(node, widget.name)) return;

    // Salvar propriedades originais
    if (!origProps[widget.name]) {
        origProps[widget.name] = {
            origType: widget.type,
            origComputeSize: widget.computeSize
        };
    }

    // Método 1: Vue frontend (v1.42+) — propriedade hidden
    widget.hidden = !show;

    // Método 2: LiteGraph legacy — type swap
    widget.type = show ? origProps[widget.name].origType : HIDDEN_TYPE;
    widget.computeSize = show ? origProps[widget.name].origComputeSize : () => [0, -4];

    // Método 3: DOM direto (se widget tem element)
    if (widget.element) {
        widget.element.hidden = !show;
        widget.element.style.display = show ? "" : "none";
    }
}

function updateSlotVisibility(node) {
    const numWidget = getWidget(node, "num_loras");
    if (!numWidget) return;
    const num = numWidget.value;

    for (let i = 1; i <= MAX_LORAS; i++) {
        const show = i <= num;
        toggleWidget(node, getWidget(node, `lora_${i}_name`), show);
        toggleWidget(node, getWidget(node, `lora_${i}_strength`), show);
        toggleWidget(node, getWidget(node, `lora_${i}_enabled`), show);
    }

    // Forçar recalculo de tamanho
    const sz = node.computeSize();
    node.setSize([Math.max(node.size[0], sz[0]), sz[1]]);
    node.setDirtyCanvas?.(true, true);
}

app.registerExtension({
    name: "MLV.LoraStack.DynamicSlots",

    async nodeCreated(node) {
        if (node.comfyClass !== NODE_CLASS) return;

        const numWidget = getWidget(node, "num_loras");
        if (!numWidget) return;

        // Hook num_loras change
        const origNumCallback = numWidget.callback;
        numWidget.callback = function (value) {
            if (origNumCallback) origNumCallback.apply(this, arguments);
            updateSlotVisibility(node);
        };

        // Auto-increment: último slot visível recebe LoRA → num_loras++
        for (let i = 1; i <= MAX_LORAS; i++) {
            const nameWidget = getWidget(node, `lora_${i}_name`);
            if (!nameWidget) continue;

            const origNameCb = nameWidget.callback;
            nameWidget.callback = function (value) {
                if (origNameCb) origNameCb.apply(this, arguments);
                const currentNum = numWidget.value;
                if (i === currentNum && value !== "None" && currentNum < MAX_LORAS) {
                    numWidget.value = currentNum + 1;
                    updateSlotVisibility(node);
                }
            };
        }

        // Visibilidade inicial com delay para widgets totalmente inicializados
        setTimeout(() => updateSlotVisibility(node), 150);
    }
});
