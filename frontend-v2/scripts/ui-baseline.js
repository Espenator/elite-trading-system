#!/usr/bin/env node
/**
 * ui-baseline.js
 * ==============
 * Copies mockup images from docs/mockups-v3/images/ into
 * artifacts/ui-screenshots/baseline/<page>/mockup.png so that
 * ui-diff.js can compare them to current screenshots.
 *
 * Usage:
 *   node scripts/ui-baseline.js
 */

import { copyFileSync, mkdirSync, existsSync } from 'fs';
import { join, resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '../..');
const MOCKUPS   = join(REPO_ROOT, 'docs', 'mockups-v3', 'images');
const BASELINES = join(REPO_ROOT, 'artifacts', 'ui-screenshots', 'baseline');

// Map page slug → primary mockup filename (first entry is the canonical one)
const MOCKUP_MAP = [
  { page: 'dashboard',              mockup: '02-intelligence-dashboard.png'          },
  { page: 'agent-command-center',   mockup: '01-agent-command-center-final.png'      },
  { page: 'sentiment-intelligence', mockup: '04-sentiment-intelligence.png'          },
  { page: 'data-sources',           mockup: '09-data-sources-manager.png'            },
  { page: 'signal-intelligence',    mockup: '03-signal-intelligence.png'             },
  { page: 'ml-brain',               mockup: '06-ml-brain-flywheel.png'               },
  { page: 'patterns',               mockup: '07-screener-and-patterns.png'           },
  { page: 'backtesting',            mockup: '08-backtesting-lab.png'                 },
  { page: 'performance',            mockup: '11-performance-analytics-fullpage.png'  },
  { page: 'market-regime',          mockup: '10-market-regime-green.png'             },
  { page: 'trades',                 mockup: 'Active-Trades.png'                      },
  { page: 'risk',                   mockup: '13-risk-intelligence.png'               },
  { page: 'trade-execution',        mockup: '12-trade-execution.png'                 },
  { page: 'settings',               mockup: '14-settings.png'                        },
];

function main() {
  for (const { page, mockup } of MOCKUP_MAP) {
    const src  = join(MOCKUPS, mockup);
    const dest = join(BASELINES, page, 'mockup.png');

    if (!existsSync(src)) {
      console.warn(`⚠  Mockup not found: ${src}`);
      continue;
    }

    mkdirSync(join(BASELINES, page), { recursive: true });
    copyFileSync(src, dest);
    console.log(`✓  ${page}  ←  ${mockup}`);
  }

  console.log('\nBaselines copied to', BASELINES);
}

main();
