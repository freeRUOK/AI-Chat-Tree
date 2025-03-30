// filename: audio-player.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
//AI - Chat - Tree的web前端;
// 一个简单的mp3音频播放器
import { Howl } from "howler";
import { useMessageBus } from "./event-bus";
const { showMessage } = useMessageBus();
/**
 * mp3播放器
 */
export default class AudioPlayer {
  constructor() {
    /**
     * 播放资源队列和当前播放的资源
     */
    this.audioQueue = new Array();
    this.currentSound = null;
  }
  /**
   * 创建并添加一个播放资源到队列
   * 如果播放器空闲尝试播放
   * @param {*} audioBuffer 音频数据流
   * @param {*} audioType 音频数据的类型， 默认audio/mpeg
   */
  play(audioBuffer, audioType = "audio/mpeg") {
    const blob = new Blob([audioBuffer], { type: audioType });
    const audioURL = URL.createObjectURL(blob);

    this.audioQueue.push(audioURL);
    if (!this.currentSound) {
      this.playNext();
    }
  }
  /**
   * 播放队列里的下一个播放资源
   * @returns 如果播放队列是空的直接返回
   */
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
        showMessage("播放器无法播放音频");
        this.playNext();
      },
      onloaderror: () => {
        showMessage("播放器无法加载音频");
        this.playNext();
      },
    });
    this.currentSound.play();
  }
}
