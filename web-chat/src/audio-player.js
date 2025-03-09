// filename: App.vue
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
//AI - Chat - Tree的web前端;
// 一个简单的mp3音频播放器
import { Howl } from "howler";

export default class AudioPlayer {
  constructor() {
    this.audioQueue = new Array();
    this.currentSound = null;
  }
  play(audio_buf) {
    const blob = new Blob([audio_buf], { type: "audio/mpeg" });
    const audioURL = URL.createObjectURL(blob);

    this.audioQueue.push(audioURL);
    if (!this.currentSound) {
      this.playNext();
    }
  }
  playNext() {
    this.currentSound = null;
    if (this.audioQueue.length === 0) {
      return;
    }
    const nextAudioURL = this.audioQueue.shift();
    this.currentSound = new Howl({
      src: nextAudioURL,
      format: "mp3",
      html5: true,
      onend: () => {
        this.playNext();
      },
      onplayerror: () => {
        this.playNext();
      },
      onloaderror: () => {
        this.playNext();
      },
    });
    this.currentSound.play();
  }
}
