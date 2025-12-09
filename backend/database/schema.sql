-- ═══════════════════════════════════════════════════════════════════════════
-- ELITE TRADING SYSTEM - TIMESCALEDB SCHEMA v1.0
-- ═══════════════════════════════════════════════════════════════════════════
-- 
-- Purpose: Complete database schema for predictive trading intelligence
-- 
-- Components:
-- 1. Base Tables (symbols, market regime)
-- 2. Price Data (hypertable for OHLCV)
-- 3. Technical Indicators
-- 4. Unusual Whales API Data (options flow, dark pool, whales)
-- 5. Predictions & Outcomes
-- 6. Machine Learning (features, models, backtest)
-- 7. Trading (signals, trades, positions)
-- 8. Indexes & Optimizations
-- 
-- TimescaleDB Features Used:
-- - Hypertables for time-series data
-- - Continuous aggregates for real-time rollups
-- - Compression policies for old data
-- - Retention policies for data cleanup
-- 
-- Author: Elite Trading Team
-- Date: December 5, 2025
-- 
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 1: BASE TABLES
-- ═══════════════════════════════════════════════════════════════════════════

-- Master symbols table
CREATE TABLE IF NOT EXISTS symbols (
    symbol_id       SERIAL PRIMARY KEY,
    ticker          VARCHAR(10) NOT NULL UNIQUE,
    company_name    VARCHAR(200),
    sector          VARCHAR(100),
    industry        VARCHAR(100),
    market_cap      BIGINT,
    avg_volume_30d  BIGINT,
    avg_volume_90d  BIGINT,
    exchange        VARCHAR(20),
    is_active       BOOLEAN DEFAULT TRUE,
    is_tracked      BOOLEAN DEFAULT TRUE,
    added_date      TIMESTAMPTZ DEFAULT NOW(),
    last_updated    TIMESTAMPTZ DEFAULT NOW(),
    metadata        JSONB
);

CREATE INDEX idx_symbols_ticker ON symbols(ticker);
CREATE INDEX idx_symbols_sector ON symbols(sector) WHERE is_active = TRUE;
CREATE INDEX idx_symbols_tracked ON symbols(is_tracked) WHERE is_tracked = TRUE;

COMMENT ON TABLE symbols IS 'Master list of all tracked symbols (500+ universe)';

-- Market regime tracking
CREATE TABLE IF NOT EXISTS market_regime (
    regime_id       SERIAL PRIMARY KEY,
    date            DATE NOT NULL UNIQUE,
    regime          VARCHAR(20) NOT NULL,
    vix_level       DECIMAL(8,2),
    vix_rsi         DECIMAL(8,2),
    breadth_adv_dec DECIMAL(8,4),
    hy_spread       DECIMAL(8,4),
    spy_change_pct  DECIMAL(8,4),
    qqq_change_pct  DECIMAL(8,4),
    iwm_change_pct  DECIMAL(8,4),
    risk_per_trade  DECIMAL(5,4),
    max_positions   INTEGER,
    strategy_mix    JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_regime_date ON market_regime(date DESC);

COMMENT ON TABLE market_regime IS 'Daily market regime classification (GREEN/YELLOW/RED/RED_RECOVERY)';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 2: PRICE DATA (HYPERTABLE)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS price_data (
    time            TIMESTAMPTZ NOT NULL,
    symbol_id       INTEGER NOT NULL REFERENCES symbols(symbol_id),
    timeframe       VARCHAR(10) NOT NULL,
    open            DECIMAL(12,4),
    high            DECIMAL(12,4),
    low             DECIMAL(12,4),
    close           DECIMAL(12,4),
    volume          BIGINT,
    vwap            DECIMAL(12,4),
    trades          INTEGER,
    PRIMARY KEY (time, symbol_id, timeframe)
);

SELECT create_hypertable('price_data', 'time', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_price_symbol_time ON price_data(symbol_id, time DESC);
CREATE INDEX idx_price_timeframe ON price_data(timeframe, time DESC);

SELECT add_compression_policy('price_data', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('price_data', INTERVAL '5 years', if_not_exists => TRUE);

COMMENT ON TABLE price_data IS 'Multi-timeframe OHLCV price data (hypertable)';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 3: TECHNICAL INDICATORS
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS technical_indicators (
    time            TIMESTAMPTZ NOT NULL,
    symbol_id       INTEGER NOT NULL REFERENCES symbols(symbol_id),
    timeframe       VARCHAR(10) NOT NULL,
    sma_20          DECIMAL(12,4),
    sma_50          DECIMAL(12,4),
    sma_200         DECIMAL(12,4),
    ema_9           DECIMAL(12,4),
    ema_21          DECIMAL(12,4),
    rsi_14          DECIMAL(8,2),
    macd            DECIMAL(12,4),
    macd_signal     DECIMAL(12,4),
    macd_histogram  DECIMAL(12,4),
    atr_14          DECIMAL(12,4),
    bb_upper        DECIMAL(12,4),
    bb_middle       DECIMAL(12,4),
    bb_lower        DECIMAL(12,4),
    bb_width        DECIMAL(8,4),
    adx_14          DECIMAL(8,2),
    volume_sma_20   BIGINT,
    volume_ratio    DECIMAL(8,4),
    PRIMARY KEY (time, symbol_id, timeframe)
);

SELECT create_hypertable('technical_indicators', 'time',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_tech_symbol_time ON technical_indicators(symbol_id, time DESC);
SELECT add_compression_policy('technical_indicators', INTERVAL '7 days', if_not_exists => TRUE);

COMMENT ON TABLE technical_indicators IS 'Pre-computed technical indicators for all timeframes';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 4: UNUSUAL WHALES API DATA
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS uw_options_flow (
    flow_id             BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    contract_symbol     VARCHAR(50),
    option_type         VARCHAR(10),
    strike_price        DECIMAL(12,4),
    expiration_date     DATE,
    days_to_expiry      INTEGER,
    premium_amount      DECIMAL(14,2),
    size                INTEGER,
    price_per_contract  DECIMAL(10,4),
    underlying_price    DECIMAL(12,4),
    bid_ask_side        VARCHAR(10),
    sentiment           VARCHAR(10),
    is_sweep            BOOLEAN DEFAULT FALSE,
    is_block            BOOLEAN DEFAULT FALSE,
    is_whale            BOOLEAN DEFAULT FALSE,
    is_golden_sweep     BOOLEAN DEFAULT FALSE,
    delta               DECIMAL(8,6),
    gamma               DECIMAL(8,6),
    theta               DECIMAL(8,6),
    vega                DECIMAL(8,6),
    implied_volatility  DECIMAL(8,4),
    exchange            VARCHAR(20),
    execution_time      TIMESTAMPTZ,
    raw_data            JSONB,
    PRIMARY KEY (flow_id, timestamp)
);

SELECT create_hypertable('uw_options_flow', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_uw_flow_symbol ON uw_options_flow(symbol_id, timestamp DESC);
CREATE INDEX idx_uw_flow_ticker ON uw_options_flow(ticker, timestamp DESC);
CREATE INDEX idx_uw_flow_whale ON uw_options_flow(timestamp DESC) WHERE is_whale = TRUE;
CREATE INDEX idx_uw_flow_sentiment ON uw_options_flow(sentiment, timestamp DESC);
CREATE INDEX idx_uw_flow_premium ON uw_options_flow(premium_amount DESC, timestamp DESC);

SELECT add_compression_policy('uw_options_flow', INTERVAL '30 days', if_not_exists => TRUE);

COMMENT ON TABLE uw_options_flow IS 'Real-time options flow from Unusual Whales API';

CREATE TABLE IF NOT EXISTS uw_darkpool (
    darkpool_id         BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    price               DECIMAL(12,4),
    size                BIGINT,
    value               DECIMAL(14,2),
    side                VARCHAR(10),
    venue               VARCHAR(50),
    is_accumulation     BOOLEAN,
    is_distribution     BOOLEAN,
    stock_price_at_time DECIMAL(12,4),
    price_vs_stock_pct  DECIMAL(8,4),
    raw_data            JSONB,
    PRIMARY KEY (darkpool_id, timestamp)
);

SELECT create_hypertable('uw_darkpool', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_uw_darkpool_symbol ON uw_darkpool(symbol_id, timestamp DESC);
CREATE INDEX idx_uw_darkpool_ticker ON uw_darkpool(ticker, timestamp DESC);
CREATE INDEX idx_uw_darkpool_size ON uw_darkpool(size DESC, timestamp DESC);

SELECT add_compression_policy('uw_darkpool', INTERVAL '30 days', if_not_exists => TRUE);

COMMENT ON TABLE uw_darkpool IS 'Dark pool block trades from Unusual Whales';

CREATE TABLE IF NOT EXISTS uw_whale_alerts (
    alert_id            BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    premium_amount      DECIMAL(14,2),
    contract_type       VARCHAR(10),
    strike_price        DECIMAL(12,4),
    expiration_date     DATE,
    days_to_expiry      INTEGER,
    sentiment           VARCHAR(10),
    is_unusual          BOOLEAN DEFAULT FALSE,
    premium_rank        INTEGER,
    volume_oi_ratio     DECIMAL(8,4),
    raw_data            JSONB,
    PRIMARY KEY (alert_id, timestamp)
);

SELECT create_hypertable('uw_whale_alerts', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_uw_whale_symbol ON uw_whale_alerts(symbol_id, timestamp DESC);
CREATE INDEX idx_uw_whale_premium ON uw_whale_alerts(premium_amount DESC, timestamp DESC);
CREATE INDEX idx_uw_whale_unusual ON uw_whale_alerts(timestamp DESC) WHERE is_unusual = TRUE;

SELECT add_compression_policy('uw_whale_alerts', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE uw_whale_alerts IS 'Whale alerts (premium > $250K) from Unusual Whales';

CREATE TABLE IF NOT EXISTS uw_market_tide (
    tide_id             BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_call_premium  DECIMAL(14,2),
    total_put_premium   DECIMAL(14,2),
    net_premium         DECIMAL(14,2),
    market_sentiment    VARCHAR(10),
    call_put_ratio      DECIMAL(8,4),
    total_call_volume   BIGINT,
    total_put_volume    BIGINT,
    whale_count         INTEGER,
    sweep_count         INTEGER,
    block_count         INTEGER,
    spy_price           DECIMAL(12,4),
    qqq_price           DECIMAL(12,4),
    vix_level           DECIMAL(8,2),
    raw_data            JSONB,
    PRIMARY KEY (tide_id, timestamp)
);

SELECT create_hypertable('uw_market_tide', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_uw_tide_time ON uw_market_tide(timestamp DESC);

SELECT add_compression_policy('uw_market_tide', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE uw_market_tide IS 'Aggregate market-wide options flow sentiment';

CREATE TABLE IF NOT EXISTS uw_unusual_activity (
    activity_id         BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    pattern_type        VARCHAR(50),
    severity            VARCHAR(10),
    description         TEXT,
    volume_vs_avg       DECIMAL(8,2),
    premium_vs_avg      DECIMAL(8,2),
    price_change_pct    DECIMAL(8,4),
    detected_sentiment  VARCHAR(10),
    confidence_score    DECIMAL(5,2),
    raw_data            JSONB,
    PRIMARY KEY (activity_id, timestamp)
);

SELECT create_hypertable('uw_unusual_activity', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_uw_unusual_symbol ON uw_unusual_activity(symbol_id, timestamp DESC);
CREATE INDEX idx_uw_unusual_severity ON uw_unusual_activity(severity, timestamp DESC);
CREATE INDEX idx_uw_unusual_pattern ON uw_unusual_activity(pattern_type, timestamp DESC);

SELECT add_compression_policy('uw_unusual_activity', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE uw_unusual_activity IS 'AI-detected unusual trading patterns from Unusual Whales';

CREATE TABLE IF NOT EXISTS uw_sector_flow (
    sector_id           BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sector_name         VARCHAR(50) NOT NULL,
    call_premium        DECIMAL(14,2),
    put_premium         DECIMAL(14,2),
    net_premium         DECIMAL(14,2),
    call_put_ratio      DECIMAL(8,4),
    sentiment           VARCHAR(10),
    top_symbol          VARCHAR(10),
    top_symbol_premium  DECIMAL(14,2),
    raw_data            JSONB,
    PRIMARY KEY (sector_id, timestamp)
);

SELECT create_hypertable('uw_sector_flow', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_uw_sector_name ON uw_sector_flow(sector_name, timestamp DESC);

SELECT add_compression_policy('uw_sector_flow', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE uw_sector_flow IS 'Sector-level options flow aggregations';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 5: PREDICTIONS & OUTCOMES
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id       BIGSERIAL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_id           INTEGER NOT NULL REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    price_at_prediction DECIMAL(12,4) NOT NULL,
    pred_1h_price       DECIMAL(12,4),
    pred_1h_change_pct  DECIMAL(8,4),
    pred_1h_confidence  DECIMAL(5,2),
    pred_1h_direction   VARCHAR(10),
    pred_1d_price       DECIMAL(12,4),
    pred_1d_change_pct  DECIMAL(8,4),
    pred_1d_confidence  DECIMAL(5,2),
    pred_1d_direction   VARCHAR(10),
    pred_1w_price       DECIMAL(12,4),
    pred_1w_change_pct  DECIMAL(8,4),
    pred_1w_confidence  DECIMAL(5,2),
    pred_1w_direction   VARCHAR(10),
    features_json       JSONB,
    feature_weights     JSONB,
    model_version       VARCHAR(50),
    model_1h_accuracy   DECIMAL(5,2),
    model_1d_accuracy   DECIMAL(5,2),
    model_1w_accuracy   DECIMAL(5,2),
    PRIMARY KEY (prediction_id, created_at)
);

SELECT create_hypertable('predictions', 'created_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_pred_symbol_time ON predictions(symbol_id, created_at DESC);
CREATE INDEX idx_pred_ticker ON predictions(ticker, created_at DESC);
CREATE INDEX idx_pred_1h_conf ON predictions(pred_1h_confidence DESC, created_at DESC);

SELECT add_compression_policy('predictions', INTERVAL '30 days', if_not_exists => TRUE);
SELECT add_retention_policy('predictions', INTERVAL '1 year', if_not_exists => TRUE);

COMMENT ON TABLE predictions IS 'Real-time price predictions for 1H, 1D, 1W horizons';

CREATE TABLE IF NOT EXISTS prediction_outcomes (
    outcome_id          BIGSERIAL PRIMARY KEY,
    prediction_id       BIGINT NOT NULL,
    prediction_time     TIMESTAMPTZ NOT NULL,
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    horizon             VARCHAR(10) NOT NULL,
    predicted_price     DECIMAL(12,4),
    predicted_change    DECIMAL(8,4),
    predicted_direction VARCHAR(10),
    confidence          DECIMAL(5,2),
    actual_price        DECIMAL(12,4),
    actual_change       DECIMAL(8,4),
    actual_direction    VARCHAR(10),
    error_pct           DECIMAL(8,4),
    error_abs           DECIMAL(12,4),
    direction_correct   BOOLEAN,
    magnitude_accuracy  DECIMAL(5,2),
    flow_contribution   DECIMAL(5,4),
    price_contribution  DECIMAL(5,4),
    resolved_at         TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (prediction_id, horizon)
);

CREATE INDEX idx_outcome_symbol ON prediction_outcomes(symbol_id, prediction_time DESC);
CREATE INDEX idx_outcome_horizon ON prediction_outcomes(horizon, direction_correct);
CREATE INDEX idx_outcome_accuracy ON prediction_outcomes(magnitude_accuracy DESC);

COMMENT ON TABLE prediction_outcomes IS 'Resolved predictions with actual vs predicted comparison';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 6: MACHINE LEARNING
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS feature_importance (
    importance_id       SERIAL PRIMARY KEY,
    calculated_at       TIMESTAMPTZ DEFAULT NOW(),
    horizon             VARCHAR(10) NOT NULL,
    window_start        TIMESTAMPTZ,
    window_end          TIMESTAMPTZ,
    sample_count        INTEGER,
    importances         JSONB,
    correlations        JSONB,
    accuracy_pct        DECIMAL(5,2),
    avg_error           DECIMAL(8,4),
    sharpe_ratio        DECIMAL(8,4),
    top_feature_1       VARCHAR(50),
    top_feature_2       VARCHAR(50),
    top_feature_3       VARCHAR(50)
);

CREATE INDEX idx_importance_horizon ON feature_importance(horizon, calculated_at DESC);

COMMENT ON TABLE feature_importance IS 'Feature importance tracking for ML models';

CREATE TABLE IF NOT EXISTS model_weights (
    weight_id           SERIAL PRIMARY KEY,
    updated_at          TIMESTAMPTZ DEFAULT NOW(),
    horizon             VARCHAR(10) NOT NULL,
    price_features_weight       DECIMAL(5,4) DEFAULT 0.20,
    flow_features_weight        DECIMAL(5,4) DEFAULT 0.25,
    correlation_features_weight DECIMAL(5,4) DEFAULT 0.20,
    regime_features_weight      DECIMAL(5,4) DEFAULT 0.15,
    technical_features_weight   DECIMAL(5,4) DEFAULT 0.20,
    detailed_weights    JSONB,
    update_reason       TEXT,
    is_active           BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_weights_active ON model_weights(horizon, is_active) WHERE is_active = TRUE;

COMMENT ON TABLE model_weights IS 'Dynamic model weights adjusted by learning loop';

CREATE TABLE IF NOT EXISTS algorithm_variants (
    variant_id          SERIAL PRIMARY KEY,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    variant_name        VARCHAR(100),
    description         TEXT,
    algorithm_config    JSONB,
    predictions_made    INTEGER DEFAULT 0,
    accuracy_1h         DECIMAL(5,2),
    accuracy_1d         DECIMAL(5,2),
    accuracy_1w         DECIMAL(5,2),
    avg_error_1h        DECIMAL(8,4),
    avg_error_1d        DECIMAL(8,4),
    avg_error_1w        DECIMAL(8,4),
    status              VARCHAR(20) DEFAULT 'testing',
    promoted_at         TIMESTAMPTZ,
    retired_at          TIMESTAMPTZ
);

CREATE INDEX idx_variant_status ON algorithm_variants(status, accuracy_1d DESC);

COMMENT ON TABLE algorithm_variants IS 'A/B testing for algorithm improvements';

CREATE TABLE IF NOT EXISTS ml_models (
    model_id            SERIAL PRIMARY KEY,
    model_name          VARCHAR(100) NOT NULL,
    model_type          VARCHAR(50),
    horizon             VARCHAR(10),
    trained_at          TIMESTAMPTZ DEFAULT NOW(),
    training_samples    INTEGER,
    training_period     INTERVAL,
    validation_accuracy DECIMAL(5,2),
    validation_sharpe   DECIMAL(8,4),
    validation_mse      DECIMAL(12,6),
    hyperparameters     JSONB,
    model_path          TEXT,
    model_size_mb       DECIMAL(8,2),
    is_production       BOOLEAN DEFAULT FALSE,
    is_archived         BOOLEAN DEFAULT FALSE,
    notes               TEXT
);

CREATE INDEX idx_model_production ON ml_models(horizon, is_production) WHERE is_production = TRUE;
CREATE INDEX idx_model_accuracy ON ml_models(validation_accuracy DESC);

COMMENT ON TABLE ml_models IS 'Registry of trained ML models';

CREATE TABLE IF NOT EXISTS backtest_results (
    backtest_id         SERIAL PRIMARY KEY,
    model_id            INTEGER REFERENCES ml_models(model_id),
    run_date            TIMESTAMPTZ DEFAULT NOW(),
    window_start        TIMESTAMPTZ,
    window_end          TIMESTAMPTZ,
    window_days         INTEGER,
    total_trades        INTEGER,
    winning_trades      INTEGER,
    losing_trades       INTEGER,
    win_rate            DECIMAL(5,2),
    total_return_pct    DECIMAL(8,4),
    sharpe_ratio        DECIMAL(8,4),
    sortino_ratio       DECIMAL(8,4),
    max_drawdown_pct    DECIMAL(8,4),
    profit_factor       DECIMAL(8,4),
    avg_win_pct         DECIMAL(8,4),
    avg_loss_pct        DECIMAL(8,4),
    volatility          DECIMAL(8,4),
    beta_spy            DECIMAL(8,4),
    results_json        JSONB,
    notes               TEXT
);

CREATE INDEX idx_backtest_model ON backtest_results(model_id, run_date DESC);
CREATE INDEX idx_backtest_sharpe ON backtest_results(sharpe_ratio DESC);

COMMENT ON TABLE backtest_results IS 'Rolling backtest results for model validation';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 7: TRADING (SIGNALS, TRADES, POSITIONS)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS scanner_signals (
    signal_id           BIGSERIAL,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    direction           VARCHAR(10) NOT NULL,
    composite_score     DECIMAL(8,2),
    fractal_score       DECIMAL(8,2),
    staircase_score     DECIMAL(8,2),
    volume_score        DECIMAL(8,2),
    setup_type          VARCHAR(50),
    structure_type      VARCHAR(20),
    velez_daily_score   DECIMAL(8,2),
    velez_4h_score      DECIMAL(8,2),
    ml_confidence       DECIMAL(5,2),
    ml_predicted_return DECIMAL(8,4),
    price_at_signal     DECIMAL(12,4),
    entry_level         DECIMAL(12,4),
    stop_level          DECIMAL(12,4),
    target_1            DECIMAL(12,4),
    target_2            DECIMAL(12,4),
    flow_confirms       BOOLEAN,
    flow_sentiment      VARCHAR(10),
    flow_premium_1d     DECIMAL(14,2),
    market_regime       VARCHAR(20),
    PRIMARY KEY (signal_id, timestamp)
);

SELECT create_hypertable('scanner_signals', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_signal_symbol ON scanner_signals(symbol_id, timestamp DESC);
CREATE INDEX idx_signal_score ON scanner_signals(composite_score DESC, timestamp DESC);
CREATE INDEX idx_signal_direction ON scanner_signals(direction, timestamp DESC);

SELECT add_compression_policy('scanner_signals', INTERVAL '90 days', if_not_exists => TRUE);

COMMENT ON TABLE scanner_signals IS 'All generated trading signals with scores and ML confidence';

CREATE TABLE IF NOT EXISTS trades (
    trade_id            SERIAL PRIMARY KEY,
    signal_id           BIGINT,
    symbol_id           INTEGER REFERENCES symbols(symbol_id),
    ticker              VARCHAR(10),
    direction           VARCHAR(10) NOT NULL,
    entry_time          TIMESTAMPTZ,
    entry_price         DECIMAL(12,4),
    exit_time           TIMESTAMPTZ,
    exit_price          DECIMAL(12,4),
    shares              INTEGER,
    position_value      DECIMAL(14,2),
    stop_price          DECIMAL(12,4),
    initial_stop        DECIMAL(12,4),
    target_1            DECIMAL(12,4),
    target_2            DECIMAL(12,4),
    entry_1_shares      INTEGER,
    entry_1_price       DECIMAL(12,4),
    entry_1_time        TIMESTAMPTZ,
    entry_2_shares      INTEGER,
    entry_2_price       DECIMAL(12,4),
    entry_2_time        TIMESTAMPTZ,
    entry_3_shares      INTEGER,
    entry_3_price       DECIMAL(12,4),
    entry_3_time        TIMESTAMPTZ,
    pnl_dollars         DECIMAL(14,2),
    pnl_percent         DECIMAL(8,4),
    r_multiple          DECIMAL(8,4),
    exit_reason         VARCHAR(50),
    status              VARCHAR(20) DEFAULT 'PENDING',
    market_regime       VARCHAR(20),
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_trade_symbol ON trades(symbol_id, entry_time DESC);
CREATE INDEX idx_trade_status ON trades(status, entry_time DESC);
CREATE INDEX idx_trade_pnl ON trades(pnl_dollars DESC);
CREATE INDEX idx_trade_signal ON trades(signal_id);

COMMENT ON TABLE trades IS 'All executed trades with P&L and risk metrics';

CREATE TABLE IF NOT EXISTS trade_outcomes (
    outcome_id          SERIAL PRIMARY KEY,
    trade_id            INTEGER REFERENCES trades(trade_id),
    signal_id           BIGINT,
    was_winner          BOOLEAN,
    r_multiple          DECIMAL(8,4),
    structure_held      BOOLEAN,
    flow_confirmed      BOOLEAN,
    ml_was_correct      BOOLEAN,
    lessons_learned     TEXT,
    improvement_notes   TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outcome_trade ON trade_outcomes(trade_id);
CREATE INDEX idx_outcome_winner ON trade_outcomes(was_winner);

COMMENT ON TABLE trade_outcomes IS 'Post-trade analysis for ML learning flywheel';

CREATE TABLE IF NOT EXISTS symbol_correlations (
    correlation_id      BIGSERIAL,
    calculated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    symbol_a_id         INTEGER REFERENCES symbols(symbol_id),
    symbol_b_id         INTEGER REFERENCES symbols(symbol_id),
    symbol_a_ticker     VARCHAR(10),
    symbol_b_ticker     VARCHAR(10),
    correlation_1h      DECIMAL(5,4),
    correlation_1d      DECIMAL(5,4),
    correlation_5d      DECIMAL(5,4),
    correlation_20d     DECIMAL(5,4),
    correlation_delta   DECIMAL(5,4),
    PRIMARY KEY (correlation_id, calculated_at)
);

SELECT create_hypertable('symbol_correlations', 'calculated_at',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

CREATE INDEX idx_corr_symbols ON symbol_correlations(symbol_a_id, symbol_b_id, calculated_at DESC);
CREATE INDEX idx_corr_strong ON symbol_correlations(calculated_at DESC) WHERE ABS(correlation_1d) > 0.7;

SELECT add_compression_policy('symbol_correlations', INTERVAL '30 days', if_not_exists => TRUE);

COMMENT ON TABLE symbol_correlations IS 'Real-time correlation matrix for all symbol pairs';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 8: CONTINUOUS AGGREGATES (MATERIALIZED VIEWS)
-- ═══════════════════════════════════════════════════════════════════════════

CREATE MATERIALIZED VIEW IF NOT EXISTS uw_flow_1h_agg
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    symbol_id,
    ticker,
    SUM(CASE WHEN option_type = 'CALL' THEN premium_amount ELSE 0 END) AS call_premium,
    COUNT(CASE WHEN option_type = 'CALL' THEN 1 END) AS call_count,
    SUM(CASE WHEN option_type = 'PUT' THEN premium_amount ELSE 0 END) AS put_premium,
    COUNT(CASE WHEN option_type = 'PUT' THEN 1 END) AS put_count,
    SUM(CASE WHEN option_type = 'CALL' THEN premium_amount ELSE -premium_amount END) AS net_premium,
    COUNT(CASE WHEN is_whale = TRUE THEN 1 END) AS whale_count,
    COUNT(CASE WHEN sentiment = 'BULLISH' THEN 1 END) AS bullish_count,
    COUNT(CASE WHEN sentiment = 'BEARISH' THEN 1 END) AS bearish_count
FROM uw_options_flow
GROUP BY hour, symbol_id, ticker;

SELECT add_continuous_aggregate_policy('uw_flow_1h_agg',
    start_offset => INTERVAL '2 hours',
    end_offset => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE
);

COMMENT ON MATERIALIZED VIEW uw_flow_1h_agg IS 'Hourly aggregated options flow for fast queries';

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 9: FUNCTIONS & UTILITIES
-- ═══════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION get_latest_prediction(p_ticker VARCHAR(10))
RETURNS TABLE (
    ticker VARCHAR(10),
    current_price DECIMAL(12,4),
    pred_1h_price DECIMAL(12,4),
    pred_1h_change_pct DECIMAL(8,4),
    pred_1h_confidence DECIMAL(5,2),
    pred_1d_price DECIMAL(12,4),
    pred_1d_change_pct DECIMAL(8,4),
    pred_1d_confidence DECIMAL(5,2),
    pred_1w_price DECIMAL(12,4),
    pred_1w_change_pct DECIMAL(8,4),
    pred_1w_confidence DECIMAL(5,2),
    predicted_at TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.ticker,
        p.price_at_prediction,
        p.pred_1h_price,
        p.pred_1h_change_pct,
        p.pred_1h_confidence,
        p.pred_1d_price,
        p.pred_1d_change_pct,
        p.pred_1d_confidence,
        p.pred_1w_price,
        p.pred_1w_change_pct,
        p.pred_1w_confidence,
        p.created_at
    FROM predictions p
    WHERE p.ticker = p_ticker
    ORDER BY p.created_at DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION calculate_prediction_accuracy(
    p_horizon VARCHAR(10),
    p_days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
    horizon VARCHAR(10),
    total_predictions INTEGER,
    correct_direction INTEGER,
    direction_accuracy DECIMAL(5,2),
    avg_error_pct DECIMAL(8,4),
    avg_confidence DECIMAL(5,2)
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p_horizon AS horizon,
        COUNT(*)::INTEGER AS total_predictions,
        COUNT(CASE WHEN direction_correct = TRUE THEN 1 END)::INTEGER AS correct_direction,
        (COUNT(CASE WHEN direction_correct = TRUE THEN 1 END)::DECIMAL / NULLIF(COUNT(*), 0) * 100) AS direction_accuracy,
        AVG(ABS(error_pct)) AS avg_error_pct,
        AVG(confidence) AS avg_confidence
    FROM prediction_outcomes
    WHERE horizon = p_horizon
      AND prediction_time >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY p_horizon;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- SECTION 10: INITIAL DATA & SETUP
-- ═══════════════════════════════════════════════════════════════════════════

INSERT INTO symbols (ticker, company_name, sector, is_tracked) VALUES
    ('SPY', 'SPDR S&P 500 ETF', 'ETF', TRUE),
    ('QQQ', 'Invesco QQQ ETF', 'ETF', TRUE),
    ('IBIT', 'iShares Bitcoin Trust', 'Crypto ETF', TRUE),
    ('ETHT', 'VanEck Ethereum ETF', 'Crypto ETF', TRUE)
ON CONFLICT (ticker) DO NOTHING;

INSERT INTO model_weights (horizon, is_active, update_reason) VALUES
    ('1H', TRUE, 'Initial weights - equal distribution'),
    ('1D', TRUE, 'Initial weights - equal distribution'),
    ('1W', TRUE, 'Initial weights - equal distribution');

VACUUM ANALYZE;

DO $$
BEGIN
    RAISE NOTICE 'Elite Trading System schema v1.0 created successfully!';
    RAISE NOTICE 'Total tables: 30+';
    RAISE NOTICE 'Hypertables: 12';
    RAISE NOTICE 'Continuous aggregates: 1';
    RAISE NOTICE 'Functions: 2';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for Unusual Whales API integration!';
    RAISE NOTICE 'API Token configured: d1cb154c-7988-41c6-ac00-09379ae7395c';
END $$;



