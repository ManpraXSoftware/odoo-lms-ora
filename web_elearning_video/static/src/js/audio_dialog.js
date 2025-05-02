/** @odoo-module **/

import { Component, useState, useRef, onMounted, xml, onRendered, onWillUnmount} from "@odoo/owl";
import { Mutex } from "@web/core/utils/concurrency";
import { Dialog } from '@web/core/dialog/dialog';
import { useWowlService } from '@web/legacy/utils';
import { useService } from "@web/core/utils/hooks";

export class AudioDialog extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.mutex = new Mutex();
        this.constraints = { audio: true, video: false };
        this.mediaRecorder = null;
        this.recordedBlobs = [];
        this.notificationService = useService("notification");
        onMounted(this._setupAudioElements.bind(this));
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
        });
    }

    _setupAudioElements() {
        this.$recordDot = document.querySelector('.record-dot');
        this.$recordTimer = document.querySelector('.record-timer');
        this.startBtn = $('button.note-record-btn');
        this.stopBtn = $('button.note-record-stop-btn');
        this.playBtn = $('button.note-video-play');
        this.downloadBtn = $('button.note-video-download');
        this.recordedAudio = $('audio.recorded');
        var self = this;
        navigator.mediaDevices.getUserMedia(this.constraints)
            .then(stream => {
                self.stream = stream;
                window.stream = stream;
                self._showControlButtons();
            })
            .catch(error => {
                self._showMicrophoneErrorMessage();
                self._hideControlButtons();
                // alert("Error accessing microphone: " + error);
            });
    }

    _showMicrophoneErrorMessage() {
        var audioContainer = $('div.audios');
        if (audioContainer.length === 0) {
            console.error("Error: Audio container not found.");
            return;
        }
        audioContainer.html(`
            <div class="microphone-error-message" style="
                width: 100%;
                text-align: center;
                color: red;
                padding: 10px;
                font-size: 16px;
                border-radius: 5px;
            ">
                ⚠️ Microphone not detected! Please enable your microphone.
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
     * Hide control buttons when the Microphone is not enabled.
     */
    _hideControlButtons() {
        this.startBtn.hide();
        this.stopBtn.hide();
        this.playBtn.hide();
        this.downloadBtn.hide();
    }

    /**
     * Show control buttons when the Microphone is enabled.
     */
    _showControlButtons() {
        this.startBtn.show();
        this.stopBtn.show();
        this.playBtn.show();
        this.downloadBtn.show();
    }

    async onStartRecording(ev) {
        try {
            this.mediaRecorder = new MediaRecorder(window.stream);
            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.recordedBlobs.push(event.data);
                }
            };
        } catch (e0) {
            alert('MediaRecorder is not supported by this browser.');
            return;
        }
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
    }

    onStopRecording(ev) {
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
    
    onPlayAudio(ev) {
        ev.preventDefault();
        var type = (this.recordedBlobs[0] || {}).type;
        var superBuffer = new Blob(this.recordedBlobs, { type });
        this.recordedAudio.get(0).src = window.URL.createObjectURL(superBuffer);
    }

    onDownloadAudio(ev) {
        ev.preventDefault();
        if (this.recordedBlobs.length === 0) {
            this.env.services.notification.add(
                "No recording available to download.",
                { type: "danger" }
            );
            return;
        }
        const blob = new Blob(this.recordedBlobs, { type: "audio/webm" });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.style.display = 'none';
        a.href = url;
        a.download = "recording.webm";
        document.body.appendChild(a);
        a.click();
        setTimeout(function () {
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        }, 100);
    }

    async save() {
        if (!this.recordedBlobs || this.recordedBlobs.length === 0) {
            this.notificationService.add("No Audio recorded to save.", {
                type: 'danger',
            });
            return;
        }
        const saveRecordedAudio = this.recordedBlobs.length > 0;
        if (saveRecordedAudio) {
            const elements = await this.mutex.exec(async () => {
                const attachmentObj = await this.addAttachment(this.recordedBlobs);
                if (!attachmentObj || !attachmentObj.id) {
                    this.notificationService.add("Failed to upload the recorded audio.", {
                        type: 'danger',
                    });
                    return [];
                }
    
                // Stop the stream if exists
                if (typeof window.stream === "object") {
                    window.stream.getTracks().forEach(track => track.stop());
                }
    
                // Clear the temporary video source
                const recordedAudio = $('audio.recorded');
                if (recordedAudio && recordedAudio.length) {
                    recordedAudio.get(0).removeAttribute('src');
                    recordedAudio.get(0).load();
                }
    
                const src = `${window.location.origin}/web/content/${attachmentObj.id}?controls=1`;
    
                const audioElement = $(`
                    <div class="media-audio" data-oe-expression="${src}">
                        <div class="css_editable_mode_display"/>
                        <div class="media_iframe_video_size" contenteditable="false" style="padding-bottom:10px;"></div>
                        <audio controls>
                            <source src="${src}" type="audio/mpeg" />
                        </audio>
                    </div>
                `)[0];
    
                if (this.props.media) {
                    audioElement.classList.add(...this.props.media.classList);
                    const style = this.props.media.getAttribute('style');
                    if (style) {
                        audioElement.setAttribute('style', style);
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
    
                return [audioElement];
            });
    
            if (elements && elements.length) {
                if (this.props.multiImages) {
                    await this.props.save(elements);
                } else {
                    await this.props.save(elements[0]);
                }
            }
        }
        // Close the dialog or perform additional actions
        this.props.close();
    }
    
    // Additional helper methods remain the same
    
    async blobToBase64(blob) {
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        return new Promise(resolve => {
            reader.onloadend = () => {
                resolve(reader.result);
            };
        });
    }
    
    async addAttachment() {
        let audioAttachment;
        if (this.recordedBlobs) {
            let type = (this.recordedBlobs[0] || {}).type;
            let superBuffer = new Blob(this.recordedBlobs, { type });
            const bs64Audio = await this.blobToBase64(superBuffer);
            audioAttachment = await this.rpc('/web_editor/attachment/add_data', {
                'name': 'recording.webm',
                'data': bs64Audio.split(',')[1],
                'is_image': false,
            });
        }
        return audioAttachment;
    }
    
}
AudioDialog.template = 'web_elearning_video.AudioDialog';
AudioDialog.defaultProps = {
    useMediaLibrary: true,
};
AudioDialog.components = {
    Dialog,
};


export class AudioDialogWrapper extends Component {
    setup() {
        this.dialogs = useWowlService('dialog');

        onRendered(() => {
            this.dialogs.add(AudioDialog, this.props);
        });
    }
}
AudioDialogWrapper.template = xml``;