// filename: message-collection.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 消息列表
import Message from "./message.js";
/** 消息列表 */
export default class MessageCollection {
  constructor() {
    this.messages = new Array();
  }
  put(msg) {
    this.messages.push(msg);
  }

  all() {
    return this.Messages;
  }
}
