/** @odoo-module **/
    import { registry } from "@web/core/registry";
    import { _t } from "@web/core/l10n/translation";
    import { WebsiteOraWysiwyg } from "@website_ora_elearning/components/website_ora_wysiwyg";
    import { Interaction } from "@web/public/interaction";
    import { browser } from "@web/core/browser/browser";
    import { isMobileOS } from "@web/core/browser/feature_detection";
    
    export class WebsiteOraFullscreen extends Interaction {
    static selector = ".o_wslides_ora_fullscreen";
    
        setup () {
           const def = super.setup(...arguments);
            if (this.editableMode) {
                return def;
            }
            var self = this;
            this.el.querySelectorAll("textarea.o_wysiwyg_loader").forEach((textareaEl) => {
                const props = {
                    textareaEl,
                    fullEdit: true,
                    getRecordInfo: () => ({
                        context: this.services.website_page.context,
                        resModel: "open.response.user.line",
                        resId: +browser.location.pathname.split("-").slice(-1)[0].split("/")[0],
                    }),
                    resizable: !isMobileOS(),
                    height: "100px",
                    // }),
                };
                const wysiwygWrapper = textareaEl.closest(".o_wysiwyg_textarea_wrapper");
                textareaEl.style.display = "none";
                textareaEl.required = false;
                wysiwygWrapper.after(textareaEl);
                wysiwygWrapper.replaceChildren();
                this.mountComponent(wysiwygWrapper, WebsiteOraWysiwyg, props);
            });
            $('.custom_response').click(function () {
                var id = this.id.split('-')[this.id.split('-').length - 1];
                var button = $(this);
                $('#collapse_div_' + id).on('shown.bs.collapse', function () {
                    button.children().text(_t('Hide Response'));
                });
                $('#collapse_div_' + id).on('hidden.bs.collapse', function () {
                    button.children().text(_t('View Response'));
                });
            });            
            return Promise.all([def]);
        }
    }
registry
    .category("public.interactions")
    .add("website_ora_elearning.website_ora_fullscreen_response", WebsiteOraFullscreen
);
