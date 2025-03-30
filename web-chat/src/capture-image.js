// filename: capture-image.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
//AI - Chat - Tree的web前端;
// 处理拍照

class CaptureImage {
  constructor() {
    this.imageCapture = null;
    this.currentFacingMode = "environment";
    this.stream = null;
  }
  // 初始化镜头
  async initCapture(facingMode) {
    try {
      const constraints = { video: { facingMode } };
      this.stream = await navigator.mediaDevices.getUserMedia(constraints);
      const track = this.stream.getVideoTracks()[0];
      this.imageCapture = new ImageCapture(track);
      this.currentFacingMode = facingMode;
    } catch (err) {
      this.imageCapture = null;
      this.stream = null;
      return false;
    }
    return true;
  }
  // 切换镜头
  async switchCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
      this.stream = null;
    }
    this.currentFacingMode =
      this.currentFacingMode === "user" ? "environment" : "user";
    return this.initCamera(this.currentFacingMode);
  }
  // 拍照
  async capture() {
    if (!this.imageCapture) return null;
    try {
      const blob = await this.imageCapture.takePhoto();
      return blob;
    } catch (err) {
      return null;
    }
  }
  // 释放镜头资源
  releaseCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach((track) => track.stop());
    }
    this.stream = null;
    this.CaptureImage = null;
  }
}
