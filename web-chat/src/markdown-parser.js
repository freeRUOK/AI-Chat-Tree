// filename: markdown-parser.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 解析markdown文档片段， 并且对代码块添加拷贝按钮
import { marked } from "marked";
/**
 * 创建一个markdown解析器
 * @returns {function-}解析函数
 */
function MarkdownParser() {
  let cache = "";
  let isCode = false;
  // 解析函数
  return function (line) {
    if (line.trim().startsWith("```")) {
      isCode = !isCode;
    }
    if (isCode) {
      cache += line;
    }

    if (!isCode && cache !== "") {
      let code = marked(cache);
      cache = "";
      code = `<div><button class="copy-code">Copy Code</button>${code}</div>`;
      return code;
    }
    return marked(isCode ? "" : line);
  };
}

export default MarkdownParser;
