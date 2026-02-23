import js from "@eslint/js";
import typescript from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import importPlugin from "eslint-plugin-import";
import simpleImportSort from "eslint-plugin-simple-import-sort";
import jsxA11y from "eslint-plugin-jsx-a11y";
import globals from "globals";

export default [
  js.configs.recommended,
  ...typescript.configs.recommended,
  jsxA11y.flatConfigs.recommended,
  {
    plugins: {
      "react-hooks": reactHooks,
      import: importPlugin,
      "simple-import-sort": simpleImportSort,
    },
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
      },
      parserOptions: {
        ecmaVersion: "latest",
        sourceType: "module",
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    settings: {
      "import/resolver": {
        typescript: {
          project: "./tsconfig.json",
        },
      },
    },
    rules: {
      // TypeScript rules
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          destructuredArrayIgnorePattern: "^_",
        },
      ],
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/explicit-function-return-type": "off",
      "@typescript-eslint/explicit-module-boundary-types": "off",
      "@typescript-eslint/no-non-null-assertion": "warn",
      // Type-aware rules (disabled - require parserOptions.project)
      "@typescript-eslint/prefer-nullish-coalescing": "off",
      "@typescript-eslint/prefer-optional-chain": "off",
      "@typescript-eslint/no-unnecessary-condition": "off",
      "@typescript-eslint/strict-boolean-expressions": "off",
      "@typescript-eslint/no-floating-promises": "off",
      "@typescript-eslint/await-thenable": "off",
      "@typescript-eslint/require-await": "off",

      // React Hooks rules
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",

      // Import rules
      "import/no-unresolved": "off",
      "import/order": "off", // Using simple-import-sort instead
      "simple-import-sort/imports": [
        "warn",
        {
          groups: [
            // React and Next.js
            ["^react", "^next", "^next/"],
            // Packages
            ["^@?\\w"],
            // Alias imports (@/)
            ["^@/"],
            // Parent imports
            ["^\\.\\.(?!/?$)", "^\\.\\./?$"],
            // Relative imports
            ["^\\./(?=.*/)(.*/)?", "^\\.(?!/?$)", "^\\./?$"],
            // Side effects
            ["^\\u0000"],
            // Style imports
            ["^.+\\.s?css$"],
          ],
        },
      ],
      "simple-import-sort/exports": "warn",
      "import/first": "error",
      "import/newline-after-import": "warn",
      "import/no-duplicates": "warn",
      "import/no-cycle": "off",
      "import/no-self-import": "error",
      "import/no-useless-path-segments": "warn",
      "import/no-named-as-default": "warn",

      // General code quality
      "no-console": ["warn", { allow: ["warn", "error"] }],
      "no-debugger": "warn",
      "no-unused-expressions": "warn",
      "no-duplicate-imports": "warn",
      "prefer-const": "warn",
      "prefer-template": "warn",
      eqeqeq: ["warn", "always", { null: "ignore" }],
      curly: ["warn", "multi-line"],
      "no-throw-literal": "error",
      "no-return-await": "warn",
      "prefer-promise-reject-errors": "warn",

      // Accessibility
      "jsx-a11y/alt-text": "warn",
      "jsx-a11y/anchor-has-content": "warn",
      "jsx-a11y/anchor-is-valid": "warn",
      "jsx-a11y/click-events-have-key-events": "warn",
      "jsx-a11y/no-static-element-interactions": "warn",

      // Turn off problematic rules
      "no-restricted-syntax": "off",
      "no-continue": "off",
      "no-param-reassign": "off",
    },
  },
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "dist/**",
      "**/*.config.js",
      "**/*.config.mjs",
      "**/*.config.cjs",
      "eslint.config.cjs",
      "eslint.config.mjs",
    ],
  },
];
