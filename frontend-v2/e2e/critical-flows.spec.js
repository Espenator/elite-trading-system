// @ts-check
import { test, expect } from '@playwright/test';

/**
 * Critical E2E Flows for Embodier Trader (frontend-only)
 * Run: npx playwright test e2e/critical-flows.spec.js
 *
 * These tests run WITHOUT a backend server.
 * They verify the React app boots, routes resolve, and pages
 * render without crashing (no error boundary, no stuck spinner).
 *
 * Backend API contract tests are skipped in CI — they require
 * a running FastAPI server on port 8000.
 */

const BASE = process.env.BASE_URL || 'http://localhost:3000';
const API  = process.env.API_URL  || 'http://localhost:8000';
const HAS_BACKEND = process.env.HAS_BACKEND === 'true';

// ---- 1. App Boot ----
test.describe('App Boot', () => {
  test('loads the app and reaches /dashboard', async ({ page }) => {
    await page.goto(BASE);
    // The app should eventually land on /dashboard (redirect or default)
    await page.waitForURL('**/dashboard', { timeout: 15000 });
    await expect(page).toHaveURL(/dashboard/);
  });
});

// ---- 2. All 14 Sidebar Pages Render Without Crash ----
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
      // Should NOT show React error boundary
      await expect(
        page.locator('text=Something went wrong')
      ).not.toBeVisible({ timeout: 8000 });
      // Page should have *some* rendered content (not blank)
      const body = page.locator('body');
      await expect(body).not.toBeEmpty();
    });
  }
});

// ---- 3. Agent Command Center Tab Navigation ----
test.describe('ACC Tab Navigation', () => {
  test('tab buttons are present', async ({ page }) => {
    await page.goto(`${BASE}/agents`);
    await page.waitForTimeout(2000);
    // Should have multiple buttons (tab bar)
    const buttons = await page.locator('button').count();
    expect(buttons).toBeGreaterThan(0);
  });
});

// ---- 4. Settings Tab Navigation ----
test.describe('Settings Tab Navigation', () => {
  test('settings page loads', async ({ page }) => {
    await page.goto(`${BASE}/settings`);
    await page.waitForTimeout(2000);
    // Should have rendered content
    const body = page.locator('body');
    await expect(body).not.toBeEmpty();
  });
});

// ---- 5. Backend API Contract Tests (skipped without backend) ----
test.describe('Backend API Contracts', () => {
  test.skip(!HAS_BACKEND, 'Skipped — no backend server (set HAS_BACKEND=true to run)');

  test('GET /api/v1/status returns 200', async ({ request }) => {
    const res = await request.get(`${API}/api/v1/status`);
    expect(res.ok()).toBeTruthy();
  });

  test('POST /api/v1/alignment/preflight returns valid schema', async ({ request }) => {
    const res = await request.post(`${API}/api/v1/alignment/preflight`, {
      data: { symbol: 'SPY', side: 'buy', quantity: 1, strategy: 'manual' },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(typeof body.allowed).toBe('boolean');
    if (!body.allowed) {
      expect(typeof body.blockedBy).toBe('string');
    }
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
