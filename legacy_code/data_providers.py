import requests
import pandas as pd
import yfinance as yf

FINVIZ_LONG_URL = "https://elite.finviz.com/screener.ashx?v=411&f=sh_avgvol_o500,sh_price_o10,ta_perf_1wup,ta_sma20_pa,ta_sma50_pa,ft_4&o=-change"
FINVIZ_SHORT_URL = "https://elite.finviz.com/screener.ashx?v=111&f=sh_avgvol_o500,sh_price_o10,ta_perf_1wdown,ta_sma20_pb,ta_sma50_pb,ft_4&o=-change"


def fetch_finviz_candidates(signal_type="LONG"):
    """Pull momentum candidates from Finviz screener based on signal_type."""
    url = FINVIZ_LONG_URL if signal_type == "LONG" else FINVIZ_SHORT_URL
    resp = requests.get(url)
    df = pd.read_html(resp.text)[-1]  # Last table usually contains the list
    candidates = df['Ticker'].dropna().astype(str).tolist()
    return candidates


def fetch_yfinance_data(symbol, period="1mo", interval="1d"):
    """Get OHLCV data from yfinance."""
    ticker = yf.Ticker(symbol)
    data = ticker.history(period=period, interval=interval)
    return data.reset_index()


def fetch_unusual_whales_flow(symbol):
    """Dummy placeholder: Replace with real Unusual Whales API code."""
    # return {'premium': 0, 'call_bias': 50, 'put_bias': 50}
    return {}
def get_structural_scores(df):
    # Implement your fractal/momentum scoring from TradingBible here.
    # Example: Use clean HHHL / LLLH detection and basic volume spike check
    import numpy as np
    scores = []
    for idx in range(4, len(df)):
        high_seq = df['High'][idx-4:idx]
        low_seq = df['Low'][idx-4:idx]
        close_seq = df['Close'][idx-4:idx]
        vol_seq = df['Volume'][idx-4:idx]
        # Uptrend/Downtrend checks
        is_hhhl = (high_seq[-1] > high_seq[0]) and (low_seq[-1] > low_seq[0])
        is_lllh = (high_seq[-1] < high_seq[0]) and (low_seq[-1] < low_seq[0])
        vol_spike = vol_seq[-1] > 1.5 * np.mean(vol_seq[:-1])
        if is_hhhl and vol_spike:
            structure = "HHHL"
            score = 60
        elif is_lllh and vol_spike:
            structure = "LLLH"
            score = 60
        else:
            structure = "Consolidation"
            score = 30
        scores.append({'score': score, 'structure': structure, 'vol_spike': vol_spike})
    return scores

def smart_candidate_filter(signal_type="LONG"):
    """Everything in one function to get candle/volume ready tickers with signals."""
    candidates = fetch_finviz_candidates(signal_type)
    output = []
    for symbol in candidates:
        yf_data = fetch_yfinance_data(symbol)
        scores = get_structural_scores(yf_data)
        top = scores[-1] if scores else None
        if top and top['score'] >= 40:
            uw_flow = fetch_unusual_whales_flow(symbol)
            output.append({
                'symbol': symbol,
                'score': top['score'],
                'structure': top['structure'],
                'vol_spike': top['vol_spike'],
                'flow_data': uw_flow
            })
    return output

