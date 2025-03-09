const path = require("path");
const { VueLoaderPlugin } = require("vue-loader");
const HtmlWebpackPlugin = require("html-webpack-plugin");

module.exports = {
  mode: "development", // 可以设置为 'development' 或 'production'
  entry: "./src/main.js", // 项目入口文件
  output: {
    path: path.resolve(__dirname, "dist"), // 输出目录
    filename: "bundle.js", // 输出文件名
    clean: true, // 每次构建前清空输出目录
  },
  module: {
    rules: [
      {
        test: /\.vue$/,
        loader: "vue-loader",
      },
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: "babel-loader", // 使用 Babel 转译 JavaScript
      },
      {
        test: /\.css$/,
        use: ["style-loader", "css-loader"],
      },
      // 可以根据需要添加其他规则，例如图片、字体等
    ],
  },
  resolve: {
    // 如果你的项目中不使用 Vue 3，可以删除或注释掉下面这行
    // alias: {
    //   vue: '@vue/compat',
    // },
    extensions: [".js", ".vue", ".json"],
  },
  plugins: [
    new VueLoaderPlugin(), // 用于支持 .vue 文件
    new HtmlWebpackPlugin({
      template: "./src/index.html", // 指定模板文件
    }),
    // 可以添加其他插件
  ],
  devServer: {
    static: {
      directory: path.join(__dirname, "dist"),
    },
    compress: true,
    port: 3000, // 你可以选择任何可用的端口
    open: true, // 启动时自动打开浏览器
    hot: true, // 启用热模块替换
    // 代理 socket.io 连接

    proxy: [
      {
        context: ["/socket.io"],
        target: "http://localhost:8001",
        ws: true,
        changeOrigin: true,
      },
    ],
  },
  // Vue 3 使用了新的渲染器，不需要 vue-template-compiler
};
