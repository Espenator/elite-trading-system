"""FINVIZ ELITE SCANNER v3.1.3 - MAXIMALIST FUNNEL EXPANSION - Bible-Aligned Trading System"""
import sys
import argparse
import pandas as pd
from datetime import datetime
from finvizfinance.screener.overview import Overview
from elite_mode_config import ELITE_MODE_CONFIG
from elite_scoring_engine import calculate_elite_score

VERBOSE_MODE = True

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def configure_maximalist_universe(scan_mode='elite'):
    config = ELITE_MODE_CONFIG.get(scan_mode, ELITE_MODE_CONFIG['elite'])
    if VERBOSE_MODE:
        print(f"\n{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGE 0: MAXIMALIST UNIVERSE CONFIGURATION{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
        print(f"  Target Universe Size: {Colors.BOLD}8,500+ stocks{Colors.ENDC}")
        print(f"  Price Range: ${config['min_price']} - ${config['max_price']:,}")
        print(f"  Min Volume: {config['min_volume']:,}")
        print(f"  Min Composite Score: {config['min_composite_score']}")
        print(f"  Mode: {Colors.BOLD}{scan_mode.upper()}{Colors.ENDC}\n")
    return config

def fetch_finviz_universe(direction='long'):
    if VERBOSE_MODE:
        print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGE 1: FETCHING FINVIZ UNIVERSE{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
    try:
        fviz = Overview()
        filters_dict = {'Average Volume': 'Over 100K'}
        if direction == 'long':
            filters_dict['Performance'] = 'Today Up'
        elif direction == 'short':
            filters_dict['Performance'] = 'Today Down'
        if VERBOSE_MODE:
            print(f"  Applying FinViz filters:")
            for key, value in filters_dict.items():
                print(f"     {key}: {value}")
            print(f"\n  Fetching data from FinViz API...\n")
        fviz.set_filter(filters_dict=filters_dict)
        df = fviz.screener_view()
        if df is None or df.empty:
            if VERBOSE_MODE:
                print(f"  {Colors.WARNING}No stocks returned from FinViz{Colors.ENDC}\n")
            return pd.DataFrame()
        if VERBOSE_MODE:
            print(f"  {Colors.OKGREEN}Successfully fetched {len(df)} stocks{Colors.ENDC}\n")
        return df
    except Exception as e:
        if VERBOSE_MODE:
            print(f"  {Colors.FAIL}Error fetching FinViz data: {str(e)}{Colors.ENDC}\n")
        return pd.DataFrame()

def apply_quality_baseline(df, direction='long', config=None):
    if df.empty:
        return df
    if config is None:
        config = ELITE_MODE_CONFIG['elite']
    if VERBOSE_MODE:
        print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGE 2: QUALITY BASELINE FILTERING{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
    numeric_cols = ['Price', 'Change', 'Volume']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('%', '').str.replace(',', ''), errors='coerce')
    df = df[(df['Price'] >= config['min_price']) & (df['Price'] <= config['max_price'])]
    df = df[df['Volume'] >= config['min_volume']]
    if direction == 'long':
        df = df[df['Change'] > 0]
    elif direction == 'short':
        df = df[df['Change'] < 0]
    if VERBOSE_MODE:
        print(f"  {Colors.OKGREEN}Quality baseline complete: {len(df)} candidates{Colors.ENDC}\n")
    return df

def apply_quality_ranking(df, direction='long'):
    if df.empty:
        return df
    if VERBOSE_MODE:
        print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGE 2.5: QUALITY RANKING{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
    df['volume_score'] = (df['Volume'] / df['Volume'].max()) * 30
    df['momentum_score'] = (abs(df['Change']) / abs(df['Change']).max()) * 20
    df['liquidity_score'] = (df['Volume'] * df['Price']).rank(pct=True) * 15
    df['structure_score'] = 35
    df['composite_score'] = (df['volume_score'] + df['momentum_score'] + df['liquidity_score'] + df['structure_score']).round(2)
    df = df.sort_values('composite_score', ascending=False)
    if VERBOSE_MODE:
        print(f"  {Colors.OKGREEN}Quality ranking complete{Colors.ENDC}\n")
    return df

def apply_elite_scoring(df, direction='long'):
    if df.empty:
        return df
    if VERBOSE_MODE:
        print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGE 3: ELITE SCORING{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
    results = []
    for idx, row in df.iterrows():
        try:
            ticker = row['Ticker']
            score_data = calculate_elite_score(ticker=ticker, price=row['Price'], volume=row['Volume'], change=row['Change'], composite_score=row['composite_score'], direction=direction)
            result_row = row.to_dict()
            result_row.update(score_data)
            results.append(result_row)
        except Exception as e:
            continue
    results_df = pd.DataFrame(results)
    if VERBOSE_MODE:
        print(f"  {Colors.OKGREEN}Elite scoring complete: {len(results_df)} candidates{Colors.ENDC}\n")
    return results_df

def apply_threshold_filter(df, config=None):
    if df.empty:
        return df
    if config is None:
        config = ELITE_MODE_CONFIG['elite']
    if VERBOSE_MODE:
        print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGE 4: THRESHOLD FILTERING{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
    if 'elite_score' in df.columns:
        df = df[df['elite_score'] >= config['min_composite_score']]
    else:
        df = df[df['composite_score'] >= config['min_composite_score']]
    if VERBOSE_MODE:
        print(f"  {Colors.OKGREEN}Threshold filtering complete: {len(df)} ELITE candidates{Colors.ENDC}\n")
    return df

def apply_final_validation(df, direction='long'):
    if df.empty:
        return df
    if VERBOSE_MODE:
        print(f"{Colors.BOLD}{Colors.OKCYAN}{'='*79}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}STAGES 5-7: FINAL VALIDATION{Colors.ENDC}")
        print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")
        print(f"  Stage 5-7: Pending implementation\n")
    return df

def export_results(df, direction='long', scan_mode='elite'):
    if df.empty:
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"elite_scan_{direction}_{scan_mode}_{timestamp}.csv"
    try:
        export_cols = ['Ticker', 'Company', 'Sector', 'Price', 'Change', 'Volume', 'composite_score', 'elite_score']
        available_cols = [col for col in export_cols if col in df.columns]
        df[available_cols].to_csv(filename, index=False)
        if VERBOSE_MODE:
            print(f"  {Colors.OKGREEN}Results exported to: {filename}{Colors.ENDC}\n")
        return filename
    except Exception as e:
        return None

def display_results(df, direction='long'):
    if df.empty:
        print(f"\n{Colors.WARNING}NO {direction.upper()} CANDIDATES FOUND{Colors.ENDC}\n")
        return
    print(f"\n{Colors.BOLD}{Colors.OKGREEN}{'='*79}")
    print(f"FINAL {direction.upper()} CANDIDATES - {len(df)} ELITE STOCKS")
    print(f"{'='*79}{Colors.ENDC}\n")
    display_df = df.head(20)
    for idx, row in display_df.iterrows():
        ticker = row['Ticker']
        company = row.get('Company', 'N/A')[:40]
        price = row['Price']
        change = row['Change']
        volume = row['Volume']
        elite_score = row.get('elite_score', row.get('composite_score', 0))
        change_color = Colors.OKGREEN if change > 0 else Colors.FAIL
        print(f"{Colors.BOLD}{ticker:6}{Colors.ENDC} | {company:40} | ${price:7.2f} | {change_color}{change:+6.2f}%{Colors.ENDC} | Vol: {volume/1000000:6.2f}M | Score: {Colors.BOLD}{elite_score:5.1f}{Colors.ENDC}")
    print(f"{Colors.OKCYAN}{'='*79}{Colors.ENDC}\n")

def run_elite_scan(direction='long', scan_mode='elite', export=False):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*79}")
    print(f"FINVIZ ELITE SCANNER v3.1.3 - MAXIMALIST FUNNEL")
    print(f"{'='*79}{Colors.ENDC}\n")
    config = configure_maximalist_universe(scan_mode)
    df = fetch_finviz_universe(direction)
    if df.empty:
        print(f"{Colors.FAIL}Failed to fetch universe{Colors.ENDC}\n")
        return None
    df = apply_quality_baseline(df, direction, config)
    if df.empty:
        print(f"{Colors.WARNING}No candidates passed quality baseline{Colors.ENDC}\n")
        return None
    df = apply_quality_ranking(df, direction)
    df = apply_elite_scoring(df, direction)
    if df.empty:
        print(f"{Colors.WARNING}No candidates passed elite scoring{Colors.ENDC}\n")
        return None
    df = apply_threshold_filter(df, config)
    if df.empty:
        print(f"{Colors.WARNING}No candidates passed threshold{Colors.ENDC}\n")
        return None
    df = apply_final_validation(df, direction)
    display_results(df, direction)
    if export:
        export_results(df, direction, scan_mode)
    return df

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FINVIZ ELITE SCANNER v3.1.3')
    parser.add_argument('--scan', type=str, choices=['long', 'short', 'both'], default='long', help='Scan direction')
    parser.add_argument('--mode', type=str, choices=['elite', 'aggressive', 'conservative'], default='elite', help='Scan mode')
    parser.add_argument('--export', action='store_true', help='Export results to CSV')
    args = parser.parse_args()
    if args.scan == 'both':
        run_elite_scan(direction='long', scan_mode=args.mode, export=args.export)
        run_elite_scan(direction='short', scan_mode=args.mode, export=args.export)
    else:
        run_elite_scan(direction=args.scan, scan_mode=args.mode, export=args.export)














