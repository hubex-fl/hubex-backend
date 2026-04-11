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
      // Sprint 5.d — the lesson from the Sprint 3.8-hotfix DeviceDetail
      // REAL-18/19 freeze: two components (UModal + UEntitySelect) were
      // used in the template but never imported, so Vue rendered them as
      // unknown HTML elements and leaked ~400px of raw DOM into the
      // page flow (completely bypassing v-if + Teleport). This rule
      // catches that pattern at lint time. Allows HTML + SVG + Vue
      // built-ins + RouterLink/RouterView from vue-router.
      "vue/no-undef-components": [
        "error",
        {
          ignorePatterns: [
            // Built-in Vue components
            "component",
            "Component",
            "transition",
            "Transition",
            "transition-group",
            "TransitionGroup",
            "keep-alive",
            "KeepAlive",
            "suspense",
            "Suspense",
            "teleport",
            "Teleport",
            "slot",
            // vue-router
            "RouterLink",
            "router-link",
            "RouterView",
            "router-view",
            // vue-i18n built-in
            "I18nT",
            "i18n-t",
          ],
        },
      ],
    },
  },
];
