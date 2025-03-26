odoo.define('web_elearning_video.wysiwyg', function (require) {
    'use strict';

    var wysiwyg = require('web_editor.wysiwyg');
    var core = require('web.core');
    var _t = core._t;
    var AudioInsertDialog = require('web_elearning_video.AudioInsertDialog');
    
    wysiwyg.include({
        _getCommands: function () {
            const commands = this._super.apply(this, arguments);
            var self = this;
            commands.push({
                groupName: _t('Medias'),
                title: _t('Video'),
                description: _t('Insert a video file.'),
                fontawesome: 'fa-file-video-o',
                callback: () => {
                    this.openMediaDialog({noVideos: false, noImages: true, noIcons: true, noDocuments: true});
                },
            });
            commands.push({
                groupName: _t('Medias'),
                title: _t('Audio'),
                description: _t('Insert an audio file.'),
                fontawesome: 'fa-file-audio-o',
                callback: () => {
                    new AudioInsertDialog(this, {
                        onAudioInsert: function (audioUrl) {
                            let audioTag = `<audio controls><source src="${audioUrl}" type="audio/mpeg"></audio>`;
                            self.odooEditor.execCommand('insertHTML', audioTag);
                        },
                    }).open();
                },
            });            
            return commands;
        },
    });
});