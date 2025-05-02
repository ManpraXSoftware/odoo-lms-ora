/** @odoo-module **/

import { Component, useState, useRef, onMounted, xml, onRendered, onWillUnmount} from "@odoo/owl";
import { Mutex } from "@web/core/utils/concurrency";
import { Dialog } from '@web/core/dialog/dialog';
import { useWowlService } from '@web/legacy/utils';
import { useService } from "@web/core/utils/hooks";

export class VideoDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.mutex = new Mutex();
        this.notificationService = useService("notification");
        this.constraints = { audio: true, video: true };
        this.mediaRecorder = null;
        this.recordedBlobs = [];
        this.notificationService = useService("notification");
        onMounted(this._setupVideoElements.bind(this));
        onWillUnmount(() => {
            if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
                this.mediaRecorder.stop();
            }
            if (this.stream) {
                this.stream.getTracks().forEach((track) => track.stop());
            }
            if (this.timerInterval) {
                clearInterval(this.timerInterval);
            }
            this.recordedBlobs = [];
        });
    }

    _setupVideoElements() {
        this.$gumVideo = document.querySelector('.gum');
        this.$recordedVideo = document.querySelector('.note-video-input');
        this.$recordDot = document.querySelector('.record-dot');
        this.$recordTimer = document.querySelector('.record-timer');
        this.startBtn = $('button.note-record-btn');
        this.stopBtn = $('button.note-record-stop-btn');
        this.playBtn = $('button.note-video-play');
        this.downloadBtn = $('button.note-video-download');

        var self = this;
        navigator.mediaDevices.getUserMedia(this.constraints)
        .then(stream => {
            if(!stream || stream.getVideoTracks().length === 0) {
                self._showCameraErrorMessage();
                self._hideControlButtons();
                return;
            }
            self.stream = stream;
            self.$gumVideo.srcObject = stream;
            window.stream = stream;
            self._showControlButtons();
        })
        .catch(error => {
            self._showCameraErrorMessage();
            self._hideControlButtons();
        });
    }

    _showCameraErrorMessage() {
        var videoContainer = $('div.videos');
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
        if (this.$recordDot) {
            this.$recordDot.style.display = 'none';
        }
        if (this.$recordTimer) {
            this.$recordTimer.style.display = 'none';
        }
    }

    /**
     * Hide control buttons when the camera is not enabled.
     */
    _hideControlButtons() {
        this.startBtn.hide();
        this.stopBtn.hide();
        this.playBtn.hide();
        this.downloadBtn.hide();
    }

    /**
     * Show control buttons when the camera is enabled.
     */
    _showControlButtons() {
        this.startBtn.show();
        this.stopBtn.show();
        this.playBtn.show();
        this.downloadBtn.show();
    }
    
    async onStartRecording() {
        this.recordedBlobs = [];
        try {
            this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    this.recordedBlobs.push(event.data);
                }
            };
            this.mediaRecorder.onstop = () => {
                // Create blob for recorded video
                const blob = new Blob(this.recordedBlobs, { type: 'video/webm' });
                if (this.$recordedVideo) {
                    this.$recordedVideo.src = window.URL.createObjectURL(blob);
                    this.$recordedVideo.muted = false;
                }

                // Enable playback and download buttons
                if (this.$playBtn) this.$playBtn.disabled = false;
                if (this.$downloadBtn) this.$downloadBtn.disabled = false;
            };

            // Start recording
            this.mediaRecorder.start();
            this.startBtn[0].disabled = true;
            this.stopBtn[0].disabled = false;
            this.playBtn[0].disabled = true;
            this.downloadBtn[0].disabled = true;
            this.$recordDot.style.display = 'block';
            this.$recordTimer.style.display = 'block';

            // Start timer
            let seconds = 0;
            this.timerInterval = setInterval(() => {
                seconds++;
                const minutes = Math.floor(seconds / 60);
                const secs = seconds % 60;
                if (this.$recordTimer) {
                    this.$recordTimer.textContent = `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                }
            }, 1000);
        } catch (err) {
            console.error('Error starting video recording:', err);
            this.notification.add('Failed to access camera/microphone. Please check permissions.', {
                title: 'Recording Error',
                type: 'danger',
            });
        }
    }

    onStopRecording() {
        this.mediaRecorder.stop();
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        this.$recordDot.style.display = 'none';
        this.startBtn[0].disabled = false;
        this.stopBtn[0].disabled = true;
        this.playBtn[0].disabled = false;
        this.downloadBtn[0].disabled = false;
    }
    
    onPlayVideo() {
        if (this.$recordedVideo) {
            this.$recordedVideo.play();
        }
    }

    onDownloadVideo() {
        const blob = new Blob(this.recordedBlobs, { type: 'video/webm' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        a.download = `recording_${new Date().toISOString()}.webm`;
        document.body.appendChild(a);
        a.click();
        setTimeout(() => {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
    }

    async save() {
        // Validate recording blob existence
        if (!this.recordedBlobs || this.recordedBlobs.length === 0) {
            this.notificationService.add("No video recorded to save.", {
                type: 'danger',
            });
            return;
        }
    
        const saveRecordedVideo = this.recordedBlobs.length > 0;
    
        if (saveRecordedVideo) {
            const elements = await this.mutex.exec(async () => {
                const attachmentObj = await this.addAttachment(this.recordedBlobs);
                if (!attachmentObj || !attachmentObj.id) {
                    this.notificationService.add("Failed to upload the recorded video.", {
                        type: 'danger',
                    });
                    return [];
                }
    
                // Stop the stream if exists
                if (typeof window.stream === "object") {
                    window.stream.getTracks().forEach(track => track.stop());
                }
    
                // Clear the temporary video source
                const recordedVideo = $('.note-video-input');
                if (recordedVideo && recordedVideo.length) {
                    recordedVideo.get(0).removeAttribute('src');
                    recordedVideo.get(0).load();
                }
    
                const src = `${window.location.origin}/web/content/${attachmentObj.id}?controls=1`;
    
                const videoElement = $(`
                    <div class="media-video" data-oe-expression="${src}">
                        <div class="css_editable_mode_display"/>
                        <div class="media_iframe_video_size" contenteditable="false" style="padding-bottom:10px;"></div>
                        <video controls>
                            <source src="${src}" type="video/webm" />
                        </video>
                    </div>
                `)[0];
    
                // Clean and transfer classes or styles from existing media if present
                if (this.props.media) {
                    videoElement.classList.add(...this.props.media.classList);
                    const style = this.props.media.getAttribute('style');
                    if (style) {
                        videoElement.setAttribute('style', style);
                    }
                    const parentEl = this.props.media.parentElement;
                    if (
                        parentEl &&
                        parentEl.tagName === "A" &&
                        parentEl.children.length === 1 &&
                        this.props.media.tagName === "IMG"
                    ) {
                        parentEl.replaceWith(parentEl.firstElementChild);
                    }
                }
    
                return [videoElement];
            });
    
            if (elements && elements.length) {
                if (this.props.multiImages) {
                    await this.props.save(elements);
                } else {
                    await this.props.save(elements[0]);
                }
            }
        }
    
        this.props.close();
    }
    
    async blobToBase64(blob) {
        return new Promise(resolve => {
            const reader = new FileReader();
            reader.onloadend = () => resolve(reader.result);
            reader.readAsDataURL(blob);
        });
    }
    
    async addAttachment(blobs) {
        if (!blobs.length) return null;
        const superBuffer = new Blob(blobs, { type: 'video/webm' });
        const bs64Video = await this.blobToBase64(superBuffer);
        const response = await this.rpc('/web_editor/attachment/add_data', {
            name: 'recording.webm',
            data: bs64Video.split(',')[1],
            is_image: false,
        });
        return response;
    }

}
VideoDialog.template = 'web_elearning_video.VideoDialog';
VideoDialog.defaultProps = {
    useMediaLibrary: true,
};
VideoDialog.components = {
    Dialog,
};


export class VideoDialogWrapper extends Component {
    setup() {
        this.dialogs = useWowlService('dialog');

        onRendered(() => {
            this.dialogs.add(VideoDialog, this.props);
        });
    }
}
VideoDialogWrapper.template = xml``;