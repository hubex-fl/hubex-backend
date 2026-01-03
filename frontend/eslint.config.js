import js from "@eslint/js";
import vue from "eslint-plugin-vue";
import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import vueParser from "vue-eslint-parser";
import globals from "globals";

const baseTsRules = {
  "no-undef": "off",
  "no-unused-vars": "off",
  "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
};

export default [
  {
    ignores: ["node_modules/**", "dist/**"],
  },
  js.configs.recommended,
  {
    files: ["**/*.ts", "**/*.tsx"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
      },
      globals: {
        ...globals.browser,
        ...globals.node,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
    },
    rules: baseTsRules,
  },
  {
    files: ["**/*.vue"],
    languageOptions: {
      parser: vueParser,
      parserOptions: {
        parser: tsParser,
        ecmaVersion: "latest",
        sourceType: "module",
      },
      globals: {
        ...globals.browser,
      },
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      vue,
    },
    rules: {
      ...baseTsRules,
      "@typescript-eslint/no-unused-vars": ["error", { args: "none" }],
      "no-empty": "off",
      "vue/multi-word-component-names": "off",
    },
  },
];
