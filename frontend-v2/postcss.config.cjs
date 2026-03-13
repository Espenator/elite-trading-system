/** PostCSS config (CJS) — required when package.json has "type": "module".
 *  Vite's PostCSS loader uses require(); ESM postcss.config.js can fail to load. */
const path = require("path");

module.exports = {
  plugins: {
    tailwindcss: { config: path.join(__dirname, "tailwind.config.cjs") },
    autoprefixer: {},
  },
};
