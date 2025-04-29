/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import Wysiwyg from 'web_editor.wysiwyg';
import { ComponentWrapper } from "web.OwlCompatibility";
import { AudioDialogWrapper } from './audio_dialog';
import { VideoDialogWrapper } from './video_dialog';
const OdooEditorLib = require('@web_editor/js/editor/odoo-editor/src/OdooEditor');
const preserveCursor = OdooEditorLib.preserveCursor;

Wysiwyg.include({
    _getPowerboxOptions: function () {
        const options = this._super.apply(this, arguments);
        const { commands, categories } = options;

        categories.push({ name: _t('Media'), priority: 50 });
        commands.push({
            category: _t('Media'),
            name: _t('Video Recorder'),
            description: _t('Insert a video.'),
            fontawesome: 'fa-file-video-o',
            callback: (params = {}) => {
                const editable = this.$editable;
                const {resModel, resId, field, type } = this._getRecordInfo(editable);
                const restoreSelection = preserveCursor(this.odooEditor.document);
                this.mediaDialogWrapper = new ComponentWrapper(this, VideoDialogWrapper, {
                    title: _t('Select a media'),
                    resModel,
                    resId,
                    useMediaLibrary: !!(field && (resModel === 'ir.ui.view' && field === 'arch' || type === 'html')),
                    media: params.node,
                    save: this._onMediaDialogSave.bind(this, {
                        node: params.node,
                        restoreSelection: restoreSelection,
                    }),
                    onAttachmentChange: this._onAttachmentChange.bind(this),
                });
                return this.mediaDialogWrapper.mount(document.body);
            },
        });

        commands.push({
            category: _t('Media'),
            name: _t('Audio'),
            description: _t('Insert an audio.'),
            fontawesome: 'fa-file-audio-o',
            callback: (params = {}) => {
                const editable = this.$editable;
                const {resModel, resId, field, type } = this._getRecordInfo(editable);
                const restoreSelection = preserveCursor(this.odooEditor.document);
                this.mediaDialogWrapper = new ComponentWrapper(this, AudioDialogWrapper, {
                    title: _t('Select a media'),
                    resModel,
                    resId,
                    useMediaLibrary: !!(field && (resModel === 'ir.ui.view' && field === 'arch' || type === 'html')),
                    media: params.node,
                    save: this._onMediaDialogSave.bind(this, {
                        node: params.node,
                        restoreSelection: restoreSelection,
                    }),
                    onAttachmentChange: this._onAttachmentChange.bind(this),
                });
                return this.mediaDialogWrapper.mount(document.body);
            },
        });

        return { ...options, commands, categories };
    }
});
