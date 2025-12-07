export const exportToCSV = (data: any[], filename: string) => {
  if (!data || data.length === 0) {
    console.error('No data to export');
    return;
  }

  // Get headers from first object
  const headers = Object.keys(data[0]);
  
  // Create CSV content
  const csvContent = [
    headers.join(','),
    ...data.map(row => 
      headers.map(header => {
        const value = row[header];
        // Escape values with commas or quotes
        if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
          return `"${value.replace(/"/g, '""')}"`;
        }
        return value;
      }).join(',')
    )
  ].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0, 10)}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

export const exportWatchlistToCSV = (watchlist: any[]) => {
  const data = watchlist.map(item => ({
    Ticker: item.ticker,
    Name: item.name,
    Price: item.price,
    Change: item.change,
    Volume: item.volume,
    Notes: item.notes || ''
  }));
  
  exportToCSV(data, 'watchlist');
};

export const exportSignalsToCSV = (signals: any[]) => {
  const data = signals.map(signal => ({
    Time: new Date(signal.timestamp).toLocaleTimeString(),
    Ticker: signal.ticker,
    Tier: signal.tier,
    Score: signal.globalConfidence,
    AI_Confidence: signal.modelAgreement,
    RVOL: signal.rvol,
    Catalyst: signal.catalyst,
    Price: signal.price,
    Change: signal.percentChange
  }));
  
  exportToCSV(data, 'signals');
};
