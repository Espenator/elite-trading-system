/** @type { import("eslint").Linter.Config } */
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: ["eslint:recommended"],
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  overrides: [
    {
      files: ["**/*.jsx"],
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  ],
  ignorePatterns: ["dist", "node_modules", "*.config.js"],
};
