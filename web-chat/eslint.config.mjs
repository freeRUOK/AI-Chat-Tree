// eslint.config.js
import js from "@eslint/js";

export default [
  js.configs.recommended,

  {
    rules: {
      "no-unused-vars": "warn",
      "no-undef": "warn",
    },
  },
  { ignores: ["dist", "webpack.config.js"] },
];
