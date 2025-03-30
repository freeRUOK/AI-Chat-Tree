// filename: util.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
//AI - Chat - Tree的web前端;
// 一些工具函数的定义

import { UAParser } from "ua-parser-js";

// 获取客户端设备信息
const getDeviceInfo = (function () {
  let deviceInfo = null;
  return function () {
    if (!deviceInfo) {
      deviceInfo = new UAParser().getResult();
      let t = new UAParser();
      alert(t.getDevice());
    }
    return deviceInfo;
  };
})();

export { getDeviceInfo };
