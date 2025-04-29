odoo.define('web_elearning_video.wysiwyg', function (require) {
    'use strict';

    var wysiwyg = require('web_editor.wysiwyg');
    var core = require('web.core');
    var _t = core._t;
    var AudioInsertDialog = require('web_elearning_video.AudioInsertDialog');
    var VideoInsertDialog = require('web_elearning_video.VideoInsertDialog');

    wysiwyg.include({
        _getCommands: function () {
            const commands = this._super.apply(this, arguments);
            var self = this;
            commands.push({
                groupName: _t('Medias'),
                title: _t('Video Recorder'),
                description: _t('Insert a video file.'),
                fontawesome: 'fa-file-video-o',
                callback: () => {
                    new VideoInsertDialog(this, {
                        onVideoInsert: function (videoUrl, mimeType) {
                            // Default to MP4, fallback to WebM based on mimeType
                            let videoType = mimeType && mimeType.includes('mp4') ? 'video/mp4' : 'video/webm';
                            let videoTag = `<video controls><source src="${videoUrl}" type="${videoType}"></video>`;
                            self.odooEditor.execCommand('insertHTML', videoTag);
                        },
                    }).open();
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