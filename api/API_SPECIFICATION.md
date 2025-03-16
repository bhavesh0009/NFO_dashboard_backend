# Market Data API Specification

## Overview

This document provides a comprehensive specification for the Market Data API endpoints, with particular emphasis on the technical indicators functionality.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, the API does not require authentication.

## Endpoints

### 1. Market Summary

#### `GET /market-summary`

Returns market summary data for all available symbols, including technical indicators.

**Parameters:** None

**Response:**
```json
[
  {
    "token": "256265",
    "symbol": "RELIANCE",
    "name": "RELIANCE INDUSTRIES",
    "futures_token": "26000",
    "lotsize": 250,
    "expiry": "2025-03-27",
    "ltp": 2345.65,
    "percent_change": 1.25,
    "open": 2320.10,
    "high": 2350.75,
    "low": 2315.25,
    "close": 2318.50,
    "volume": 2500000,
    "opn_interest": 350000,
    "week_low_52": 2100.00,
    "week_high_52": 2500.00,
    "futures_ltp": 2350.80,
    "futures_percent_change": 1.35,
    "futures_volume": 150000,
    "futures_oi": 75000,
    "atm_price": 65.75,
    "atm_price_per_lot": 16437.50,
    "position_metric": 52.50,
    "sma_50": 2320.50,
    "sma_100": 2290.75,
    "sma_200": 2200.30,
    "ema_20": 2330.25,
    "ema_50": 2315.80,
    "ema_200": 2195.40,
    "rsi_14": 65.3,
    "rsi_21": 58.7,
    "volatility_21": 0.18,
    "volatility_200": 0.22,
    "sma_200_position": "ABOVE_SMA200",
    "ma_crossover_status": "BULLISH_CROSSOVER",
    "sma_200_percent_diff": 6.6
  },
  // More symbols...
]
```

#### `GET /market-summary/{symbol}`

Returns market summary data for a specific symbol.

**Parameters:**
- `symbol` (path parameter): Stock symbol to retrieve data for (case-insensitive, partial match)

**Response:** Same format as `/market-summary` but filtered for the specified symbol.

### 2. Technical Filters

#### `GET /market-summary/technical-filter`

Filter market data based on technical indicators.

**Parameters:**
- `sma_position` (query parameter): Position relative to 200-day SMA
  - Possible values: `ABOVE_SMA200`, `BELOW_SMA200`, `AT_SMA200`
- `crossover_status` (query parameter): MA crossover status
  - Possible values: `BULLISH_CROSSOVER`, `BEARISH_CROSSOVER`, `NEUTRAL`
- `min_rsi` (query parameter): Minimum RSI-14 value (0-100)
- `max_rsi` (query parameter): Maximum RSI-14 value (0-100)
- `min_volatility` (query parameter): Minimum 21-day volatility
- `max_volatility` (query parameter): Maximum 21-day volatility

**Response:** Same format as `/market-summary` but filtered based on the specified criteria.

**Example:**
```
GET /api/market-summary/technical-filter?sma_position=ABOVE_SMA200&min_rsi=30&max_rsi=70
```

### 3. Technical Indicators

#### `GET /technical-indicators`

Returns technical indicators summary data for all available symbols.

**Parameters:** None

**Response:**
```json
[
  {
    "token": "256265",
    "symbol_name": "RELIANCE INDUSTRIES",
    "trade_date": "2025-03-15",
    "sma_50": 2320.50,
    "sma_100": 2290.75,
    "sma_200": 2200.30,
    "ema_20": 2330.25,
    "ema_50": 2315.80,
    "ema_200": 2195.40,
    "rsi_14": 65.3,
    "rsi_21": 58.7,
    "volatility_21": 0.18,
    "volatility_200": 0.22,
    "last_close": 2345.65,
    "last_volume": 2500000
  },
  // More symbols...
]
```

#### `GET /technical-indicators/{symbol}`

Returns technical indicators summary data for a specific symbol.

**Parameters:**
- `symbol` (path parameter): Stock symbol to retrieve data for (case-insensitive, partial match)

**Response:** Same format as `/technical-indicators` but filtered for the specified symbol.

## Technical Indicator Fields

### Simple Moving Averages (SMA)
- `sma_50`: 50-day Simple Moving Average
- `sma_100`: 100-day Simple Moving Average
- `sma_200`: 200-day Simple Moving Average

### Exponential Moving Averages (EMA)
- `ema_20`: 20-day Exponential Moving Average
- `ema_50`: 50-day Exponential Moving Average
- `ema_200`: 200-day Exponential Moving Average

### Relative Strength Index (RSI)
- `rsi_14`: 14-day Relative Strength Index (0-100 scale)
- `rsi_21`: 21-day Relative Strength Index (0-100 scale)

### Volatility
- `volatility_21`: 21-day Historical Volatility (annualized)
- `volatility_200`: 200-day Historical Volatility (annualized)

### Derived Technical Metrics
- `sma_200_position`: Position relative to 200-day SMA
  - Possible values:
    - `ABOVE_SMA200`: Price is above 200-day SMA
    - `BELOW_SMA200`: Price is below 200-day SMA
    - `AT_SMA200`: Price is near 200-day SMA (±0.5%)
- `ma_crossover_status`: Moving Average crossover status
  - Possible values:
    - `BULLISH_CROSSOVER`: Short-term MA crossed above long-term MA
    - `BEARISH_CROSSOVER`: Short-term MA crossed below long-term MA
    - `NEUTRAL`: No recent crossover
- `sma_200_percent_diff`: Percentage difference between current price and 200-day SMA

## Using Technical Indicators in Frontend Development

### Example: Displaying Technical Indicators in a Stock Table

```javascript
// Fetch data and display in a table
async function displayStockTable() {
  const response = await fetch('http://localhost:8000/api/market-summary');
  const stocks = await response.json();
  
  const tableBody = document.getElementById('stockTableBody');
  tableBody.innerHTML = '';
  
  stocks.forEach(stock => {
    // Determine CSS classes based on technical indicators
    const rsiClass = stock.rsi_14 > 70 ? 'overbought' : stock.rsi_14 < 30 ? 'oversold' : '';
    const smaClass = stock.sma_200_position === 'ABOVE_SMA200' ? 'bullish' : 'bearish';
    
    tableBody.innerHTML += `
      <tr>
        <td>${stock.symbol}</td>
        <td>${stock.ltp}</td>
        <td>${stock.percent_change}%</td>
        <td class="${smaClass}">${stock.sma_200}</td>
        <td class="${rsiClass}">${stock.rsi_14}</td>
        <td>${stock.ma_crossover_status}</td>
        <td>${stock.volatility_21}</td>
      </tr>
    `;
  });
}
```

### Example: Technical Filter Component

```javascript
// Function to apply technical filters
async function applyTechnicalFilters() {
  const smaPosition = document.getElementById('smaPositionSelect').value;
  const minRsi = document.getElementById('minRsiInput').value;
  const maxRsi = document.getElementById('maxRsiInput').value;
  
  let url = 'http://localhost:8000/api/market-summary/technical-filter?';
  
  if (smaPosition) {
    url += `sma_position=${smaPosition}&`;
  }
  
  if (minRsi) {
    url += `min_rsi=${minRsi}&`;
  }
  
  if (maxRsi) {
    url += `max_rsi=${maxRsi}&`;
  }
  
  const response = await fetch(url);
  const filteredStocks = await response.json();
  
  // Update UI with filtered stocks
  updateStockTable(filteredStocks);
}
```

### Example: Technical Charts Integration

```javascript
// Fetch technical data for a specific symbol and create charts
async function displayTechnicalCharts(symbol) {
  const response = await fetch(`http://localhost:8000/api/technical-indicators/${symbol}`);
  const data = await response.json();
  
  if (data && data.length > 0) {
    const technicalData = data[0];
    
    // Create SMA Chart
    createLineChart('smaChart', {
      labels: ['SMA 50', 'SMA 100', 'SMA 200', 'Current Price'],
      data: [
        technicalData.sma_50, 
        technicalData.sma_100, 
        technicalData.sma_200,
        technicalData.last_close
      ]
    });
    
    // Create RSI Chart
    createGaugeChart('rsiChart', technicalData.rsi_14, {
      min: 0,
      max: 100,
      zones: [
        { min: 0, max: 30, color: 'green' },   // Oversold
        { min: 30, max: 70, color: 'yellow' }, // Neutral
        { min: 70, max: 100, color: 'red' }    // Overbought
      ]
    });
  }
}
```

## Error Handling

All endpoints return an empty array `[]` if no data is found.

## Pagination

Currently, the API does not support pagination. All data is returned in a single response.

## Rate Limiting

Currently, the API does not implement rate limiting.

## Changes and Versioning

This API is version 1.0.0. Changes to the API will be documented in future versions of this specification. 