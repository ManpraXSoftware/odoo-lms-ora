odoo.define('web_elearning_video.AudioInsertDialog', function (require) {
    'use strict';

    var Dialog = require('web.Dialog');
    var core = require('web.core');
    var _t = core._t;
    var recordedBlobs = [];

    var AudioInsertDialog = Dialog.extend({
        template: 'wysiwyg.widgets.audio',
        events: {
            'click .note-record-audio-btn': '_onClickStart',
            'click .note-record-stop-btn': '_onClickStop',
            'click .note-audio-play': '_onPlayAudio',
            'click .note-audio-download': '_onDownloadAudio',
        },

        init: function (parent, media, editable) {
            this._super(parent, _.extend({}, {
                title: _t("Add Audio"),
                buttons: [{ text: _t("Add"), classes: 'btn-primary', click: this.save },{ text: _t("Discard"), classes: 'btn-secondary', close: true }],
            }, {}));
            this.constraints = { audio: true, video: false };
            this.mediaRecorder;
            this.media = media;
            this.editable = editable;
        },
        start: function () {
            recordedBlobs = [];
            this.timerDisplay = this.$('.record-timer');
            this.recordDot = this.$('.record-dot');
            this.startButton = this.$('button.note-record-audio-btn');
            this.stopButton = this.$('button.note-record-stop-btn');
            this.playButton = this.$('button.note-audio-play');
            this.downloadButton = this.$('button.note-audio-download');
            this.recordedAudio = this.$('audio.recorded');
            navigator.mediaDevices.getUserMedia(this.constraints)
                .then(stream => {
                    window.stream = stream;
                })
                .catch(error => {
                    alert('Error accessing media devices.', error);
                });
        },

        _onClickStart: function (ev) {
            recordedBlobs = [];
            this._startTimer();
            this._showRecordDot();
            try {
                this.mediaRecorder = new MediaRecorder(window.stream);
            } catch (e0) {
                alert('MediaRecorder is not supported by this browser.');
                return;
            }
            var self = this;
            ev.currentTarget.disabled = true;
            this.stopButton.get(0).disabled = false;
            this.playButton.get(0).disabled = true;
            this.downloadButton.get(0).disabled = true
            this.mediaRecorder.ondataavailable = self.handleDataAvailable;
            this.mediaRecorder.start(10);
        },

        _onClickStop: function (ev) {
            this._stopTimer();
            this._hideRecordDot();
            this.mediaRecorder.stop();
            ev.currentTarget.disabled = true;
            this.playButton.get(0).disabled = false;
            this.startButton.get(0).disabled = false;
            this.downloadButton.get(0).disabled = false
        },

        _startTimer: function () {
            let seconds = 0;
            let minutes = 0;
            let self = this;
            this.timerDisplay.show();
            this.timerDisplay.text('00:00');
    
            this.timerInterval = setInterval(() => {
                seconds++;
                if (seconds === 60) {
                    minutes++;
                    seconds = 0;
                }
                let formattedTime = (minutes < 10 ? '0' : '') + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
                self.timerDisplay.text(formattedTime);
            }, 1000);
        },
    
        _stopTimer: function () {
            clearInterval(this.timerInterval);
            this.recordedTime = this.timerDisplay.text();
        },
        
        _showRecordDot: function () {
            this.recordDot.show();
        },

        _hideRecordDot: function () {
            this.recordDot.hide();
        },
        
        handleDataAvailable: function (event) {
            if (event.data && event.data.size > 0) {
                recordedBlobs.push(event.data);
            }
        },

        _onPlayAudio: function (ev) {
            var type = (recordedBlobs[0] || {}).type;
            var superBuffer = new Blob(recordedBlobs, { type });
            this.recordedAudio.get(0).src = window.URL.createObjectURL(superBuffer);
        },

        _onDownloadAudio: function (ev) {
            var blob = new Blob(recordedBlobs, { type: 'audio/webm' });
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'recording.webm';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () {
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }, 100);
        },
        save: async function () {
            if (recordedBlobs.length !== 0) {
                const attachmentObj = await this.addAttachment();
                this.recordedAudio.get(0).removeAttribute('src');
                this.recordedAudio.get(0).load();
                if (typeof (window.stream) == "object") {
                    window.stream.getTracks().forEach((track) => {
                        track.stop();
                    });
                }
                this.final_data = attachmentObj;
                let src = window.location.origin + '/web/content/' + attachmentObj.id + '?autoplay=0&controls=1';
                const audioUrl = $(
                    '<div class="media_iframe_audio" data-oe-expression="' + src + '">' +
                        '<div class="css_editable_mode_display">&nbsp;</div>' +
                        '<audio src="' + src + '" controls="controls" frameborder="0" contenteditable="false""></audio>' +
                    '</div>'
                );
                this.$media = audioUrl;
                this.media = this.$media[0];
                    
            }
            return Promise.resolve(this.media);
        },

        destroy: function () {
            if (typeof (window.stream) == "object") {
                window.stream.getTracks().forEach((track) => {
                    track.stop();
                });
            }
            return this._super(...arguments);
        },
        blobToBase64: blob => {
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            return new Promise(resolve => {
                reader.onloadend = () => {
                    resolve(reader.result);
                };
            });
        },
        addAttachment: async function () {
            let audioAttachment;
            if (recordedBlobs) {
                let type = (recordedBlobs[0] || {}).type;
                let superBuffer = new Blob(recordedBlobs, { type });
                const bs64Audio = await this.blobToBase64(superBuffer)
                audioAttachment = await this._rpc({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        'name': 'recording.webm',
                        'data': bs64Audio.split(',')[1],
                        'is_image': false,
                    },
                })
            }
            return audioAttachment;
        }
    });

    return AudioInsertDialog;
});