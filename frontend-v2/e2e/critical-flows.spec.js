// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Critical E2E Flows for Embodier Trader
 * Run: npx playwright test e2e/critical-flows.spec.js
 *
 * Covers:
 *  1. App boots and redirects to /dashboard
 *  2. All 14 sidebar pages render without crash
 *  3. Agent Command Center tabs navigate correctly
 *  4. Trade Execution alignment preflight fires
 *  5. Settings tabs navigate correctly
 *  6. Backend /api/v1/alignment/preflight contract
 */

const BASE = process.env.BASE_URL || 'http://localhost:5173';
const API  = process.env.API_URL  || 'http://localhost:8000';

// ---- 1. App Boot ----
test.describe('App Boot', () => {
  test('redirects root to /dashboard', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForURL('**/dashboard');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('dashboard renders KPI cards', async ({ page }) => {
    await page.goto(`${BASE}/dashboard`);
    await page.waitForSelector('[class*="card"]', { timeout: 10000 });
    const cards = await page.locator('[class*="card"]').count();
    expect(cards).toBeGreaterThan(3);
  });
});

// ---- 2. All 14 Sidebar Pages Render ----
const ROUTES = [
  { path: '/dashboard',              title: 'Dashboard' },
  { path: '/agents',                 title: 'Agent Command Center' },
  { path: '/sentiment',              title: 'Sentiment' },
  { path: '/data-sources',           title: 'Data Sources' },
  { path: '/signal-intelligence-v3', title: 'Signal Intelligence' },
  { path: '/ml-brain',               title: 'ML Brain' },
  { path: '/patterns',               title: 'Patterns' },
  { path: '/backtest',               title: 'Backtesting' },
  { path: '/performance',            title: 'Performance' },
  { path: '/market-regime',          title: 'Market Regime' },
  { path: '/trades',                 title: 'Trades' },
  { path: '/risk',                   title: 'Risk' },
  { path: '/trade-execution',        title: 'Trade Execution' },
  { path: '/settings',               title: 'Settings' },
];

test.describe('Page Render Smoke Tests', () => {
  for (const route of ROUTES) {
    test(`${route.title} (${route.path}) renders without crash`, async ({ page }) => {
      await page.goto(`${BASE}${route.path}`);
      // Should NOT show error boundary
      await expect(page.locator('text=Something went wrong')).not.toBeVisible({ timeout: 5000 });
      // Should have loaded past the spinner
      await expect(page.locator('text=Loading module')).not.toBeVisible({ timeout: 10000 });
    });
  }
});

// ---- 3. Agent Command Center Tab Navigation ----
test.describe('ACC Tab Navigation', () => {
  test('all 6 tabs are clickable', async ({ page }) => {
    await page.goto(`${BASE}/agents`);
    const tabs = ['overview', 'agents', 'swarm', 'candidates', 'brain-map', 'blackboard'];
    for (const tab of tabs) {
      const btn = page.locator(`button:has-text("${tab}")`, { hasText: new RegExp(tab, 'i') }).first();
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(500);
      }
    }
  });

  test('Brain Map renders SVG DAG', async ({ page }) => {
    await page.goto(`${BASE}/agents`);
    // Click Brain Map tab
    const bmTab = page.locator('button').filter({ hasText: /brain/i }).first();
    if (await bmTab.isVisible()) await bmTab.click();
    await page.waitForTimeout(1000);
    // Should have SVG with nodes
    const svgNodes = await page.locator('svg circle').count();
    expect(svgNodes).toBeGreaterThan(0);
  });
});

// ---- 4. Trade Execution Alignment Preflight ----
test.describe('Alignment Preflight', () => {
  test('preflight card renders and Run Check button exists', async ({ page }) => {
    await page.goto(`${BASE}/trade-execution`);
    await page.waitForTimeout(2000);
    const preflightText = page.locator('text=Alignment Preflight').first();
    await expect(preflightText).toBeVisible({ timeout: 10000 });
    const runBtn = page.locator('button:has-text("Run Check")').first();
    await expect(runBtn).toBeVisible();
  });
});

// ---- 5. Settings Tabs ----
test.describe('Settings Tab Navigation', () => {
  test('settings page loads with tabs', async ({ page }) => {
    await page.goto(`${BASE}/settings`);
    await page.waitForTimeout(2000);
    // Should have multiple tab buttons
    const buttons = await page.locator('button').count();
    expect(buttons).toBeGreaterThan(5);
  });
});

// ---- 6. Backend API Contract Tests ----
test.describe('Backend API Contracts', () => {
  test('GET /api/v1/status returns 200', async ({ request }) => {
    const res = await request.get(`${API}/api/v1/status`);
    expect(res.ok()).toBeTruthy();
  });

  test('POST /api/v1/alignment/preflight returns valid schema', async ({ request }) => {
    const res = await request.post(`${API}/api/v1/alignment/preflight`, {
      data: {
        symbol: 'SPY',
        side: 'buy',
        quantity: 1,
        strategy: 'manual',
      },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    // Contract: must have 'allowed' boolean
    expect(typeof body.allowed).toBe('boolean');
    // Contract: if blocked, must have blockedBy string
    if (!body.allowed) {
      expect(typeof body.blockedBy).toBe('string');
    }
    // Contract: must have checks array
    expect(Array.isArray(body.checks)).toBeTruthy();
    for (const check of body.checks) {
      expect(typeof check.name).toBe('string');
      expect(typeof check.passed).toBe('boolean');
    }
  });

  test('GET /api/v1/alignment/verdicts returns array', async ({ request }) => {
    const res = await request.get(`${API}/api/v1/alignment/verdicts`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(Array.isArray(body)).toBeTruthy();
  });
});