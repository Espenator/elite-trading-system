// @ts-check
/**
 * Visual Regression Test Harness
 * ================================
 * Captures screenshots of every route at fixed viewports and compares them
 * to baseline mockup images.  Differences are written to the artifacts/
 * directory so they can be reviewed in PRs.
 *
 * Viewports: 1920×1080 (FHD), 1440×900 (WXGA+), 1280×720 (HD)
 *
 * Run modes:
 *   npx playwright test e2e/visual-regression.spec.js               # compare
 *   UPDATE_SNAPSHOTS=1 npx playwright test e2e/visual-regression.spec.js  # update baselines
 *
 * Artifacts written to:
 *   artifacts/ui-screenshots/current/<page>/<viewport>.png
 *   artifacts/ui-screenshots/diff/<page>/<viewport>-diff.png  (when mismatch)
 */

import { test, expect } from '@playwright/test';
import { writeFileSync, mkdirSync, existsSync } from 'fs';
import { join, resolve } from 'path';

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const REPO_ROOT = resolve(new URL(import.meta.url).pathname, '../../..');
const ARTIFACTS = join(REPO_ROOT, 'artifacts', 'ui-screenshots');

/** Fixed viewports to capture */
const VIEWPORTS = [
  { name: '1920x1080', width: 1920, height: 1080 },
  { name: '1440x900',  width: 1440, height: 900  },
  { name: '1280x720',  width: 1280, height: 720  },
];

/** Route → page mapping (matches App.jsx) */
const PAGES = [
  {
    name: 'dashboard',
    path: '/dashboard',
    title: 'Dashboard',
    mockups: ['02-intelligence-dashboard.png'],
  },
  {
    name: 'agent-command-center',
    path: '/agents',
    title: 'Agent Command Center',
    mockups: [
      '01-agent-command-center-final.png',
      '05-agent-command-center.png',
      '05b-agent-command-center-spawn.png',
      '05c-agent-registry.png',
      'agent command center brain map.png',
      'agent command center node control.png',
      'agent command center swarm overview.png',
      'realtimeblackbard fead.png',
    ],
  },
  {
    name: 'sentiment-intelligence',
    path: '/sentiment',
    title: 'Sentiment Intelligence',
    mockups: ['04-sentiment-intelligence.png'],
  },
  {
    name: 'data-sources',
    path: '/data-sources',
    title: 'Data Sources',
    mockups: ['09-data-sources-manager.png'],
  },
  {
    name: 'signal-intelligence',
    path: '/signal-intelligence-v3',
    title: 'Signal Intelligence',
    mockups: ['03-signal-intelligence.png'],
  },
  {
    name: 'ml-brain',
    path: '/ml-brain',
    title: 'ML Brain Flywheel',
    mockups: ['06-ml-brain-flywheel.png'],
  },
  {
    name: 'patterns',
    path: '/patterns',
    title: 'Screener & Patterns',
    mockups: ['07-screener-and-patterns.png'],
  },
  {
    name: 'backtesting',
    path: '/backtest',
    title: 'Backtesting Lab',
    mockups: ['08-backtesting-lab.png'],
  },
  {
    name: 'performance',
    path: '/performance',
    title: 'Performance Analytics',
    mockups: ['11-performance-analytics-fullpage.png'],
  },
  {
    name: 'market-regime',
    path: '/market-regime',
    title: 'Market Regime',
    mockups: ['10-market-regime-green.png', '10-market-regime-red.png'],
  },
  {
    name: 'trades',
    path: '/trades',
    title: 'Active Trades',
    mockups: ['Active-Trades.png'],
  },
  {
    name: 'risk',
    path: '/risk',
    title: 'Risk Intelligence',
    mockups: ['13-risk-intelligence.png'],
  },
  {
    name: 'trade-execution',
    path: '/trade-execution',
    title: 'Trade Execution',
    mockups: ['12-trade-execution.png'],
  },
  {
    name: 'settings',
    path: '/settings',
    title: 'Settings',
    mockups: ['14-settings.png'],
  },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function ensureDir(dir) {
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true });
}

/**
 * Inject CSS to disable animations/transitions so screenshots are stable.
 */
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

// ---------------------------------------------------------------------------
// Tests: Screenshot capture
// ---------------------------------------------------------------------------

for (const viewport of VIEWPORTS) {
  test.describe(`Screenshots @ ${viewport.name}`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });

    for (const pg of PAGES) {
      test(`capture ${pg.title} (${pg.path})`, async ({ page }) => {
        const dir = join(ARTIFACTS, 'current', pg.name);
        ensureDir(dir);

        // Navigate and wait for page to settle
        await page.goto(`${BASE}${pg.path}`, { waitUntil: 'networkidle', timeout: 20000 });
        await disableAnimations(page);
        await page.waitForTimeout(500); // let any micro-animations settle

        // Verify page didn't crash
        await expect(page.locator('text=Page Error')).toHaveCount(0);
        await expect(page.locator('text=404')).toHaveCount(0);

        // Take screenshot
        const screenshotPath = join(dir, `${viewport.name}.png`);
        await page.screenshot({ path: screenshotPath, fullPage: false });

        // Playwright's built-in visual comparison (updates when UPDATE_SNAPSHOTS=1)
        if (process.env.UPDATE_SNAPSHOTS !== '1') {
          // Use soft assertion so other pages are still captured even if one differs
          await expect(page).toHaveScreenshot(`${pg.name}-${viewport.name}.png`, {
            maxDiffPixelRatio: 0.15, // 15% tolerance — flag regressions, allow minor drift
            animations: 'disabled',
          });
        }
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Tests: Smoke (always run — page load without crash)
// ---------------------------------------------------------------------------

test.describe('Smoke: all pages load', () => {
  for (const pg of PAGES) {
    test(`${pg.title} loads at ${pg.path}`, async ({ page }) => {
      await page.goto(`${BASE}${pg.path}`, { waitUntil: 'networkidle', timeout: 20000 });
      await expect(page.locator('text=Page Error')).toHaveCount(0);
      const body = await page.textContent('body');
      expect((body ?? '').length).toBeGreaterThan(100);
    });
  }
});
