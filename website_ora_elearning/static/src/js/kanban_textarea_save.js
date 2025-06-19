/** @odoo-module **/

import { onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

const { Component } = owl;

class KanbanTextareaHandler extends Component {
    static template = "website_ora_elearning.kanban_textarea";
    static props = {
        record: Object,
        readonly: Boolean,
    };

    setup() {
        onMounted(() => {
            this.textarea = document.querySelector(".kanban-textarea");
            if (this.textarea) {
                this.textarea.addEventListener("blur", this.save.bind(this));
            }
        });
    }

    async onInputChange(ev) {
        const value = ev.target.value;
        const recordId = this.props.record.resId;
        try {
            await rpc("/web/dataset/call_kw/rubric.assess.line.wizard/write", {
                model: 'rubric.assess.line.wizard',
                method: "write",
                args: [[recordId], { assess_explanation: value }],
                kwargs: {},
            });
        } catch (error) {
            console.error("Error saving textarea:", error);
        }
    }
}

export const kanbantextareahandler = {
    component: KanbanTextareaHandler,
};

registry.category("view_widgets").add("kanban_textarea_handler", kanbantextareahandler);
