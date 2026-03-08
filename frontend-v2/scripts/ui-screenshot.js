#!/usr/bin/env node
/**
 * ui-screenshot.js
 * ================
 * Standalone script: starts the Vite dev server (or uses a running one),
 * visits every route at the three standard viewports, and saves screenshots
 * to artifacts/ui-screenshots/current/<page>/<viewport>.png
 *
 * Usage:
 *   node scripts/ui-screenshot.js           # uses http://localhost:3000 if running
 *   BASE_URL=http://localhost:4173 node scripts/ui-screenshot.js
 */

import { chromium } from '@playwright/test';
import { mkdirSync, existsSync, writeFileSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '../..');
const BASE = process.env.BASE_URL || 'http://localhost:3000';
const ARTIFACTS = join(REPO_ROOT, 'artifacts', 'ui-screenshots');

const VIEWPORTS = [
  { name: '1920x1080', width: 1920, height: 1080 },
  { name: '1440x900',  width: 1440, height: 900  },
  { name: '1280x720',  width: 1280, height: 720  },
];

const PAGES = [
  { name: 'dashboard',             path: '/dashboard'              },
  { name: 'agent-command-center',  path: '/agents'                 },
  { name: 'sentiment-intelligence',path: '/sentiment'              },
  { name: 'data-sources',          path: '/data-sources'           },
  { name: 'signal-intelligence',   path: '/signal-intelligence-v3' },
  { name: 'ml-brain',              path: '/ml-brain'               },
  { name: 'patterns',              path: '/patterns'               },
  { name: 'backtesting',           path: '/backtest'               },
  { name: 'performance',           path: '/performance'            },
  { name: 'market-regime',         path: '/market-regime'          },
  { name: 'trades',                path: '/trades'                 },
  { name: 'risk',                  path: '/risk'                   },
  { name: 'trade-execution',       path: '/trade-execution'        },
  { name: 'settings',              path: '/settings'               },
];

async function disableAnimations(page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `,
  });
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const results = [];

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({
      viewport: { width: vp.width, height: vp.height },
    });
    const page = await context.newPage();

    for (const pg of PAGES) {
      const dir = join(ARTIFACTS, 'current', pg.name);
      if (!existsSync(dir)) mkdirSync(dir, { recursive: true });

      const screenshotPath = join(dir, `${vp.name}.png`);
      let status = 'ok';
      let error = null;

      try {
        await page.goto(`${BASE}${pg.path}`, { waitUntil: 'networkidle', timeout: 20000 });
        await disableAnimations(page);
        await page.waitForTimeout(500);
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`✓ ${pg.name} @ ${vp.name}  →  ${screenshotPath}`);
      } catch (e) {
        status = 'error';
        error = e.message;
        console.error(`✗ ${pg.name} @ ${vp.name}: ${e.message}`);
      }

      results.push({ page: pg.name, viewport: vp.name, path: screenshotPath, status, error });
    }

    await context.close();
  }

  await browser.close();

  const manifestPath = join(ARTIFACTS, 'current', 'manifest.json');
  writeFileSync(
    manifestPath,
    JSON.stringify({ capturedAt: new Date().toISOString(), base: BASE, screenshots: results }, null, 2),
  );
  console.log(`\nScreenshot manifest written to ${manifestPath}`);
}

main().catch(err => { console.error(err); process.exit(1); });
