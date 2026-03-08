#!/usr/bin/env node
/**
 * ui-diff.js
 * ==========
 * Compares current screenshots against mockup baselines using a pixel-level
 * approach via the 'pixelmatch' + 'pngjs' libraries.
 *
 * Input:
 *   artifacts/ui-screenshots/baseline/<page>/mockup.png  (copy of mockup)
 *   artifacts/ui-screenshots/current/<page>/<viewport>.png
 *
 * Output:
 *   artifacts/ui-screenshots/diff/<page>/<viewport>-diff.png
 *   artifacts/ui-screenshots/diff-report.json  (per-page diff scores)
 *
 * Usage:
 *   node scripts/ui-diff.js
 *   DIFF_THRESHOLD=0.10 node scripts/ui-diff.js   # custom mismatch threshold (0–1)
 */

import { writeFileSync, readFileSync, existsSync, mkdirSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '../..');
const ARTIFACTS = join(REPO_ROOT, 'artifacts', 'ui-screenshots');
const THRESHOLD  = parseFloat(process.env.DIFF_THRESHOLD ?? '0.10');

const VIEWPORTS = ['1920x1080', '1440x900', '1280x720'];

const PAGES = [
  'dashboard', 'agent-command-center', 'sentiment-intelligence',
  'data-sources', 'signal-intelligence', 'ml-brain', 'patterns',
  'backtesting', 'performance', 'market-regime', 'trades', 'risk',
  'trade-execution', 'settings',
];

/**
 * Load a PNG file using pngjs and return { data, width, height }.
 * Scales `other` to match `reference` dimensions if they differ.
 */
function loadPng(filePath) {
  const { PNG } = require('pngjs');
  const buffer = readFileSync(filePath);
  return PNG.sync.read(buffer);
}

/**
 * Resize PNG image data to targetWidth × targetHeight using nearest-neighbour.
 */
function resizePng(src, targetWidth, targetHeight) {
  const { PNG } = require('pngjs');
  const dst = new PNG({ width: targetWidth, height: targetHeight });
  const scaleX = src.width  / targetWidth;
  const scaleY = src.height / targetHeight;
  for (let y = 0; y < targetHeight; y++) {
    for (let x = 0; x < targetWidth; x++) {
      const srcX = Math.min(Math.floor(x * scaleX), src.width  - 1);
      const srcY = Math.min(Math.floor(y * scaleY), src.height - 1);
      const si = (srcY * src.width  + srcX) * 4;
      const di = (y    * targetWidth + x   ) * 4;
      dst.data[di + 0] = src.data[si + 0];
      dst.data[di + 1] = src.data[si + 1];
      dst.data[di + 2] = src.data[si + 2];
      dst.data[di + 3] = src.data[si + 3];
    }
  }
  return dst;
}

async function diffImages(baselinePath, currentPath, diffPath) {
  let pixelmatch;
  let PNG;
  try {
    ({ default: pixelmatch } = await import('pixelmatch'));
    ({ PNG } = await import('pngjs'));
  } catch {
    return { mismatchRatio: null, blocked: 'pixelmatch or pngjs not installed — run: npm install --save-dev pixelmatch pngjs' };
  }

  const imgA = PNG.sync.read(readFileSync(baselinePath));
  const imgB = PNG.sync.read(readFileSync(currentPath));

  // Use screenshot (B) dimensions as the canonical size; resize baseline if needed
  const width  = imgB.width;
  const height = imgB.height;

  const scaledA = (imgA.width === width && imgA.height === height)
    ? imgA
    : (() => {
        const dst = new PNG({ width, height });
        const sx = imgA.width  / width;
        const sy = imgA.height / height;
        for (let y = 0; y < height; y++) {
          for (let x = 0; x < width; x++) {
            const srcX = Math.min(Math.floor(x * sx), imgA.width  - 1);
            const srcY = Math.min(Math.floor(y * sy), imgA.height - 1);
            const si = (srcY * imgA.width + srcX) * 4;
            const di = (y * width + x) * 4;
            dst.data[di + 0] = imgA.data[si + 0];
            dst.data[di + 1] = imgA.data[si + 1];
            dst.data[di + 2] = imgA.data[si + 2];
            dst.data[di + 3] = imgA.data[si + 3];
          }
        }
        return dst;
      })();

  const diffPng = new PNG({ width, height });
  const mismatchPixels = pixelmatch(scaledA.data, imgB.data, diffPng.data, width, height, { threshold: 0.1 });

  writeFileSync(diffPath, PNG.sync.write(diffPng));

  const totalPixels = width * height;
  const mismatchRatio = mismatchPixels / totalPixels;
  return { mismatchPixels, totalPixels, mismatchRatio };
}

async function main() {
  const report = { generatedAt: new Date().toISOString(), threshold: THRESHOLD, pages: [] };
  let hasErrors = false;

  for (const page of PAGES) {
    const baselineDir = join(ARTIFACTS, 'baseline', page);
    const currentDir  = join(ARTIFACTS, 'current',  page);
    const diffDir     = join(ARTIFACTS, 'diff',      page);

    if (!existsSync(baselineDir)) {
      console.log(`⚠  No baseline for ${page} — skipping diff`);
      report.pages.push({ page, status: 'no-baseline', viewports: [] });
      continue;
    }

    mkdirSync(diffDir, { recursive: true });

    const viewportResults = [];

    for (const vp of VIEWPORTS) {
      const currentPath  = join(currentDir,  `${vp}.png`);
      const diffPath     = join(diffDir,     `${vp}-diff.png`);

      // Try to find a baseline at this viewport; fall back to first available mockup
      const baselinePath = join(baselineDir, `${vp}.png`);
      const mockupPath   = join(baselineDir, 'mockup.png');
      const refPath      = existsSync(baselinePath) ? baselinePath : existsSync(mockupPath) ? mockupPath : null;

      if (!refPath) {
        viewportResults.push({ viewport: vp, status: 'no-baseline' });
        continue;
      }

      if (!existsSync(currentPath)) {
        viewportResults.push({ viewport: vp, status: 'no-current' });
        continue;
      }

      try {
        const result = await diffImages(refPath, currentPath, diffPath);
        const pass = result.blocked
          ? null
          : result.mismatchRatio <= THRESHOLD;

        const status = result.blocked ? 'blocked' : pass ? 'pass' : 'fail';
        if (status === 'fail') hasErrors = true;

        console.log(
          `${status === 'pass' ? '✓' : status === 'fail' ? '✗' : '⚠'} ${page} @ ${vp}: ` +
          (result.blocked
            ? result.blocked
            : `${(result.mismatchRatio * 100).toFixed(2)}% mismatch (${result.mismatchPixels}/${result.totalPixels} px)`),
        );

        viewportResults.push({ viewport: vp, status, ...result, diffPath });
      } catch (e) {
        console.error(`✗ ${page} @ ${vp}: ${e.message}`);
        viewportResults.push({ viewport: vp, status: 'error', error: e.message });
        hasErrors = true;
      }
    }

    const pageStatus = viewportResults.every(v => v.status === 'pass')
      ? 'pass'
      : viewportResults.some(v => v.status === 'fail')
      ? 'fail'
      : 'partial';

    report.pages.push({ page, status: pageStatus, viewports: viewportResults });
  }

  const reportPath = join(ARTIFACTS, 'diff-report.json');
  writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`\nDiff report written to ${reportPath}`);

  if (hasErrors && process.env.STRICT_DIFF === '1') {
    process.exit(1);
  }
}

main().catch(err => { console.error(err); process.exit(1); });
