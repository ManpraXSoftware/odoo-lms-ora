odoo.define('wysiwyg.widgets.VideoDialog', function (require) {
    'use strict';

    var widgetsMedia = require('wysiwyg.widgets.media');
    var recordedBlobs = [];

    widgetsMedia.VideoWidget.include({
        xmlDependencies: widgetsMedia.VideoWidget.prototype.xmlDependencies.concat(
            ['/web_elearning_video/static/src/xml/video_dialog_template.xml']
        ),

        events: {
            'click .note-record-btn': '_onClickStart',
            'click .note-record-stop-btn': '_onClickStop',
            'click .note-video-play': '_onPlayVideo',
            'click .note-video-download': '_onDownloadVideo',
        },

        /**
         * @constructor
         */
        init: function (parent, media, options) {
            this._super(parent, media, options || {});
            this.constraints = { audio: true, video: true };
            this.mediaRecorder = null;
            this.media = media || null;
            this.recordedBlobs = [];
        },

        start: function () {
            recordedBlobs = [];
            this.gumVideo = this.$('video.gum').get(0);
            this.startButton = this.$('button.note-record-btn');
            this.stopButton = this.$('button.note-record-stop-btn');
            this.playButton = this.$('button.note-video-play');
            this.downloadButton = this.$('button.note-video-download');
            this.recordedVideo = this.$('video.note-video-input');
        
            var self = this;
        
            navigator.mediaDevices.getUserMedia(this.constraints)
                .then(stream => {
                    if (!stream || stream.getVideoTracks().length === 0) {
                        self._showCameraErrorMessage();
                        self._hideControlButtons();  // ✅ Hide buttons
                        return;
                    }
                    self.gumVideo.srcObject = stream;
                    window.stream = stream;
        
                    // ✅ If the camera is enabled, show the buttons
                    self._showControlButtons();
                })
                .catch(error => {
                    self._showCameraErrorMessage();
                    self._hideControlButtons();  // ✅ Hide buttons if error occurs
                });
        },
        
        /**
         * Show an error message inside the video dialog if the camera is not activated.
         */
        _showCameraErrorMessage: function () {
            var videoContainer = this.$('div.videos');
            if (videoContainer.length === 0) {
                console.error("Error: Video container not found.");
                return;
            }
            videoContainer.html(`
                <div class="camera-error-message" style="
                    width: 100%;
                    text-align: center;
                    color: red;
                    padding: 10px;
                    font-size: 16px;
                    border-radius: 5px;
                ">
                    ⚠️ Camera not detected! Please enable your camera.
                </div>
            `);
        },
        
        /**
         * Hide control buttons when the camera is not enabled.
         */
        _hideControlButtons: function () {
            this.startButton.hide();
            this.stopButton.hide();
            this.playButton.hide();
            this.downloadButton.hide();
        },
        
        /**
         * Show control buttons when the camera is enabled.
         */
        _showControlButtons: function () {
            this.startButton.show();
            this.stopButton.show();
            this.playButton.show();
            this.downloadButton.show();
        },
        
        _onClickStart: function (ev) {
            recordedBlobs = [];
            var options = { mimeType: 'video/webm;codecs=vp9', bitsPerSecond: 100000 };

            try {
                this.mediaRecorder = new MediaRecorder(window.stream, options);
            } catch (e0) {
                console.log('Unable to create MediaRecorder with options Object: ', options, e0);
                try {
                    options = { mimeType: 'video/webm;codecs=vp8', bitsPerSecond: 100000 };
                    this.mediaRecorder = new MediaRecorder(window.stream, options);
                } catch (e1) {
                    console.log('Unable to create MediaRecorder with options Object: ', options, e1);
                    try {
                        options = { mimeType: 'video/mp4' };
                        this.mediaRecorder = new MediaRecorder(window.stream, options);
                    } catch (e2) {
                        alert('MediaRecorder is not supported by this browser.');
                        console.error('Exception while creating MediaRecorder:', e2);
                        return;
                    }
                }
            }

            var self = this;
            ev.currentTarget.disabled = true;
            this.stopButton[0].disabled = false;
            this.playButton[0].disabled = true;
            this.downloadButton[0].disabled = true;
            this.mediaRecorder.ondataavailable = self.handleDataAvailable;
            this.mediaRecorder.start(10);
        },

        _onClickStop: function (ev) {
            this.mediaRecorder.stop();
            ev.currentTarget.disabled = true;
            this.playButton.get(0).disabled = false;
            this.startButton.get(0).disabled = false;
            this.downloadButton.get(0).disabled = false
        },
        handleDataAvailable: function (event) {
            if (event.data && event.data.size > 0) {
                recordedBlobs.push(event.data);
            }
        },

        _onPlayVideo: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var type = (recordedBlobs[0] || {}).type;
            var superBuffer = new Blob(recordedBlobs, { type });
            this.recordedVideo.get(0).src = window.URL.createObjectURL(superBuffer);
        },
        
        _onDownloadVideo: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            var blob = new Blob(recordedBlobs, { type: 'video/webm' });
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
                this.recordedVideo.get(0).removeAttribute('src');
                this.recordedVideo.get(0).load();
                if (typeof (window.stream) == "object") {
                    window.stream.getTracks().forEach((track) => {
                        track.stop();
                    });
                }
                this.final_data = attachmentObj;
                let url = window.location.origin + '/web/content/' + attachmentObj.id + '?controls=1';
                let videoUrl = `
                    <div class="media_iframe_video iframe_custom o_we_selected_image">
                        <div class="media_iframe_video_size" contenteditable="false" style="padding-bottom:10px;">&nbsp;</div>
                        <video controls="controls">
                            <source src="${url}" type="video/webm" />
                        </video>
                    </div><br/>`;
                var pTag = this.editable.find('p');
                if (pTag.length > 1) {
                    pTag.last().append(videoUrl);
                } else {
                    pTag.append(videoUrl);
                }
            }
            this.close();
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
            let videoAttachment;
            if (recordedBlobs) {
                let type = (recordedBlobs[0] || {}).type;
                let superBuffer = new Blob(recordedBlobs, { type });
                const bs64Video = await this.blobToBase64(superBuffer)
                videoAttachment = await this._rpc({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        'name': 'recording.webm',
                        'data': bs64Video.split(',')[2],
                        'res_id': this.defaultOptions.res_id,
                        'res_model': this.defaultOptions.res_model,
                    },
                })
            }
            return videoAttachment;
        }
    });
});