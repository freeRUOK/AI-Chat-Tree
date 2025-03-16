// filename: markdown-parser.js
// Author: FreeRUOK <2651688427@qq.com>
// Date: 2025-03
// Description: AI-Chat-Tree的web前端
// 解析markdown文档片段转换到html片段， 并且对代码块添加拷贝按钮
import { marked } from "marked";

/**
 * 创建一个流逝markdown解析器
 * 最小处理单位行
 */
export default class MarkdownParser {
  static {
    marked.setOptions({ gfm: true, pedantic: false });
  }
  /**
   *mdStatus解析器内部状态  cache解析器缓存
   */
  constructor() {
    this.cache = "";
    this.mdStatus = "line";
  }
  /**
   * 外部应当调用这个函数解析一行markdown内容
   * 该函数根据状态调用其他函数完成代码块和表格的解析
   * @param {*} line 需要解析的markdown行
   * @returns html文档片段
   */
  parseLine(line) {
    if (this.mdStatus === "code" || line.startsWith("```")) {
      return this.parseCode(line);
    } else if (this.mdStatus === "table" || line.startsWith("|")) {
      return this.parseTable(line);
    }

    return marked(line);
  }
  /**
   * 解析完整代码块，
   * 如果不是完整代码块则内部缓存， 直到完整接收代码块
   * 此函数不应当直接调用
   * 给代码块添加拷贝按钮， 后续根据class="copy-code"添加拷贝函数
   * @param {*} line markdown片段
   * @returns html片段
   */
  parseCode(line) {
    this.cache += line;
    if (
      this.mdStatus === "code" &&
      this.cache !== "" &&
      line.startsWith("```")
    ) {
      let code = marked(this.cache);
      this.cache = "";
      this.mdStatus = "line";
      code = `<div><button class="copy-code">Copy Code</button>${code}</div>`;
      return code;
    }
    this.mdStatus = "code";
    return null;
  }

  /**
   * 解析完整的表格， 不应当直接调用
   * @param {*} line markdown表格片段
   * @returns html表格片段
   */
  parseTable(line) {
    this.cache += line;
    if (!line.startsWith("|")) {
      this.mdStatus = "line";
      const table = marked(this.cache);
      this.cache = "";
      return table;
    }
    this.mdStatus = "table";
    return null;
  }
}
