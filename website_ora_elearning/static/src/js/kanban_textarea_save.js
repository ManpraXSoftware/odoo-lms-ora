/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component } = owl;

class KanbanTextareaHandler extends Component {
    setup() {
        this.rpc = useService("rpc");

        onMounted(() => {
            const textareas = document.querySelectorAll(".assess_explanation_input");
            const selects = document.querySelectorAll("[name='option_id']");

            textareas.forEach(textarea => {
                textarea.addEventListener("change", (ev) => this._onTextareaChange(ev));
                textarea.addEventListener("input", (ev) => {
                    textarea.classList.add("unsaved");
                });
            });

            selects.forEach(select => {
                select.addEventListener("mousedown", (ev) => {
                    // Before changing option_id, auto-save assess_explanation if dirty
                    const card = select.closest(".oe_kanban_card");
                    const textarea = card.querySelector(".assess_explanation_input");
                    if (textarea && textarea.classList.contains("unsaved")) {
                        this._saveTextarea(textarea);
                        textarea.classList.remove("unsaved");
                    }
                });
            });
        });
    }

    async _onTextareaChange(ev) {
        const textarea = ev.currentTarget;
        await this._saveTextarea(textarea);
        textarea.classList.remove("unsaved");
    }

    async _saveTextarea(textarea) {
        const value = textarea.value?.trim();
        const recordId = parseInt(textarea.dataset.id);
        const model = textarea.dataset.model;
        const field = textarea.dataset.field;

        if (!recordId || !model || !field) return;

        try {
            await this.rpc("/web/dataset/call_kw/" + model + "/write", {
                model: model,
                method: "write",
                args: [[recordId], { [field]: value }],
                kwargs: {},
            });
            console.log(`Saved ${field} for record ${recordId}`);
        } catch (error) {
            console.error("Error saving field:", error);
        }
    }
}

registry.category("actions").add("kanban_textarea_handler", KanbanTextareaHandler);
