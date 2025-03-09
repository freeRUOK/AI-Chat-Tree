// filename: message.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 定义用户消息或AI模型的消息
export default class Message {
  /**
   * 表示一条消息
   */
  constructor(title, body, tag = "text") {
    this.inner = { title, body, tag };
  }
  set title(value) {
    this.inner.title = value;
  }
  get title() {
    return this.inner.title;
  }

  set body(value) {
    this.inner.body = value;
  }
  get body() {
    return this.inner.body;
  }
  appendBody(part) {
    this.inner.body += part;
  }

  set tag(value) {
    this.inner.tag = value;
  }
  get tag() {
    return this.inner.tag;
  }

  toString() {
    return `title: ${this.inner.title}\nbody: ${this.inner.body}\ntag: ${this.inner.tag}\n`;
  }
}
