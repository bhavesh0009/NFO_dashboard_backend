# Angel One Data Pipeline

_Last Updated: March 16, 2025_

## Overview

This project extracts data from Angel One API and stores it in DuckDB for analysis and reporting. It provides a reliable data pipeline for financial market data.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage and Pipeline Configuration](#usage-and-pipeline-configuration)
- [Data Processing](#data-processing)
- [Real-time Market Data](#real-time-market-data)
- [Options Processing](#options-processing)
- [Technical Indicators](#technical-indicators)
- [Database Schema](#database-schema)
- [API Access](#api-access)
- [Project Structure](#project-structure)
- [License](#license)
- [Contributing](#contributing)

## Features

- ✅ **API Integration**: Secure Angel One API connection with token management
- ✅ **Token Management**: F&O and equity token handling with expiry management
- ✅ **Database Storage**: Efficient DuckDB storage with automated validation
- ✅ **Equity Market Data**: OHLCV data from 2000-present with multiple intervals
- ✅ **Process Automation**: Batched processing with rate limiting
- ✅ **Real-time Market Data**: Live market data for spot, futures, and options
- ✅ **Windows Compatibility**: ASCII-compatible logging for Windows terminals
- ✅ **Options Analytics**: Strike price normalization and strike distance calculation
- ✅ **Parquet Exports**: Real-time exports for API consumption after each data refresh
- ✅ **FastAPI Module**: REST API for accessing market data
- ✅ **Technical Indicators**: Automatically calculated technical indicators (SMA, EMA, RSI, Volatility)

## Prerequisites

- Python 3.8+
- Angel One trading account with API access
- Required Python packages (see `requirements.txt`)

## Installation

1. Clone this repository
2. Create and activate virtual environment:

   ```bash
   # Create virtual environment
   python -m venv venv

   # Activate virtual environment
   # On Windows:
   source venv/Scripts/activate  # Git Bash
   # OR
   .\venv\Scripts\activate      # Command Prompt
   # OR
   .\venv\Scripts\Activate.ps1  # PowerShell

   # On Linux/Mac:
   source venv/bin/activate
   ```

3. Install required packages:

   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. Configure your Angel One API credentials (see Configuration section)

## Configuration

The project uses a YAML-based configuration system for managing all settings:

### Environment Variables

Create a `.env` file in the project root with your API credentials:

```
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_PIN=your_pin
ANGEL_ONE_TOTP_SECRET=your_totp_secret
```

### Application Configuration

All other settings are managed in `config/config.yaml`:

```yaml
# API Configuration
api:
  angel_one:
    token_master_url: "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"

# Market Configuration
market:
  trading_hours:
    start: "09:15"  # IST
    end: "15:30"    # IST
  pre_market:
    start: "09:00"
    end: "09:15"
  post_market:
    start: "15:30"
    end: "15:45"

# Database Configuration
database:
  default_path: "nfo_derivatives_hub.duckdb"  # Central hub for NFO derivatives data

# Real-time Market Data Configuration
realtime_market_data:
  mode: "FULL"  # Mode for getMarketData API (FULL, OHLC, LTP)
  max_tokens_per_request: 50  # Maximum number of tokens per API request
  rate_limiting:
    request_delay: 1.0  # Seconds between API requests (rate limit is 1 request per second)
  refresh_interval: 60  # Seconds between real-time data refreshes
```

## Usage and Pipeline Configuration

The market data pipeline (`market_data_pipeline.py`) automates the entire data workflow from token refresh to real-time monitoring.

### Basic Commands

```bash
# Run the complete pipeline with default settings
python market_data_pipeline.py

# Run pipeline with options for ATM options only
python market_data_pipeline.py --options --exact-atm

# Skip token refresh and historical data steps
python market_data_pipeline.py --no-tokens --no-history

# Run with custom refresh interval (30 seconds)
python market_data_pipeline.py --refresh 30

# Run with limited number of tokens
python market_data_pipeline.py --equity-limit 50 --futures-limit 50

# Export market summary to Parquet manually
python utils/export_market_summary.py

# Export market summary with custom output path
python utils/export_market_summary.py --output path/to/output.parquet

# Start the API server (default port: 8000)
python scripts/run_api_server.py

# Start the API server on a specific port
python scripts/run_api_server.py --port 8080
```

### Pipeline Workflow

The pipeline follows a sequential process:

1. **Token Refresh**: Updates token master data if needed
2. **Historical Data**: Updates historical price data for equity tokens
3. **Market Hours Awareness**: Waits for market open if started before trading hours
4. **Real-time Monitoring**: Runs continuous real-time data collection at specified intervals
5. **Data Export**: Exports market summary to Parquet files after each refresh for API consumption

### Command-Line Options

The pipeline offers various configuration options:

- **Data Selection**:
  - `--no-tokens`: Skip token refresh step
  - `--no-history`: Skip historical data refresh step
  - `--history-limit N`: Limit historical data to N equity tokens
  - `--no-equity`: Exclude equity from real-time monitoring
  - `--no-futures`: Exclude futures from real-time monitoring
  - `--options`: Include options in real-time monitoring

- **Options Configuration**:
  - `--all-options`: Include all options (not just ATM)
  - `--strike-buffer N`: Number of strikes above and below ATM to include
  - `--exact-atm`: Select only the exact ATM strike (1 call + 1 put per future)

- **Timing and Limits**:
  - `--refresh N`: Real-time refresh interval in seconds (default: 60)
  - `--no-wait`: Don't wait for market open (start monitoring immediately)
  - `--equity-limit N`: Limit equity tokens in real-time monitoring
  - `--futures-limit N`: Limit futures tokens in real-time monitoring
  - `--options-limit N`: Limit options tokens in real-time monitoring

- **Output**:
  - `--verbose`: Enable verbose output with detailed logging

### Automated Scheduling

For completely automated operation, you can set up the pipeline as a scheduled task:

#### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create a Basic Task
3. Set the trigger to run daily at 8:55 AM
4. Set the action to start a program
5. Program/script: `python`
6. Arguments: `market_data_pipeline.py --options --exact-atm`
7. Start in: Your project directory

#### Linux/MacOS (crontab)

```
55 8 * * 1-5 cd /path/to/project && /path/to/python market_data_pipeline.py --options --exact-atm
```

## Data Processing

The pipeline efficiently processes three instrument types:

- **Futures**: Current expiry contracts from NFO segment with standardized dates
- **Options**: Strike price validation with distribution analysis
- **Equity**: Spot token mapping with referential integrity to futures

## Real-time Market Data

The system captures comprehensive real-time market data using Angel One's getMarketData API:

- **Full Market Data**: Complete market data including LTP, OHLC, volumes, and order book depth
- **Efficient Batching**: Respects API limits (50 tokens per request, 1 request per second)
- **Multiple Instrument Types**: Support for equity, futures, and options
- **Smart Options Filtering**: Automatically identifies and focuses on ATM options
- **Continuous Monitoring**: Scheduled data collection with market hours awareness
- **Windows Compatibility**: ASCII-compatible logging for error-free operation in Windows terminals
- **Automatic Exports**: Exports market summary data to Parquet files after each real-time data refresh

## Options Processing

The system includes intelligent options processing and analytics features:

### ATM Options Detection and Filtering

- **Selective Processing**: Fetches only At-The-Money (ATM) and near-ATM options based on futures prices
- **Configurable Buffer**: Choose specific strike range around ATM with `--strike-buffer` parameter
- **Exact ATM Mode**: Select only the single closest strike to current price with `--exact-atm` flag
- **Automatic Strike Distance**: Determines appropriate strike distances for each stock
- **Efficiency**: Reduces options processing by 90-95% compared to full options chain

### Options Analytics

- **Strike Price Normalization**: Adjusts raw strike prices to match market representation
- **Strike Distance Calculation**: Automatically identifies standard strike increments for each stock
- **Strike Grid Mapping**: Creates precise strike grid for strategy development

The focused approach to options processing provides significant performance benefits while maintaining focus on the most relevant instruments for trading analysis.

## Technical Indicators

The system includes comprehensive technical indicator calculations:

1. **Available Indicators**:
   - **Simple Moving Average (SMA)**: Available periods: 50, 100, 200 days
   - **Exponential Moving Average (EMA)**: Available periods: 20, 50, 200 days
   - **Relative Strength Index (RSI)**: Available periods: 14, 21 days
   - **Historical Volatility**: Available periods: 21, 200 days

2. **Indicator Summary Format**:
   - Wide format with one row per equity symbol
   - Organized columns for each indicator-period combination (e.g., sma_200, volatility_21)
   - Automatically updated with latest trading day calculations
   - Included in all market summary data

3. **Derived Technical Metrics**:
   - **SMA200 Position**: Whether price is above, below, or at the 200-day SMA
   - **MA Crossover Status**: Bullish or bearish moving average crossover pattern
   - **SMA200 Percent Difference**: Percentage difference between price and 200-day SMA

4. **Access via API**:
   - Technical indicators are included in the `/api/market-summary` endpoint
   - Filter stocks based on technical criteria using `/api/market-summary/technical-filter` endpoint

5. **Configuration**:
   Technical indicators are configured in the `config/config.yaml` file.

## Database Schema

The system uses the following primary tables and views:

```sql
-- Token Master Table
CREATE TABLE token_master (
    token VARCHAR,
    symbol VARCHAR,
    name VARCHAR,
    expiry DATE,
    strike DECIMAL(18,6),
    lotsize INTEGER,
    instrumenttype VARCHAR,
    exch_seg VARCHAR,
    tick_size DECIMAL(18,6),
    token_type VARCHAR,
    futures_token VARCHAR,
    strike_distance DECIMAL(18,6),
    created_at TIMESTAMP,
    PRIMARY KEY (token)
)

-- Historical Data Table
CREATE TABLE historical_data (
    token VARCHAR,
    symbol_name VARCHAR,
    timestamp TIMESTAMP,
    open DECIMAL(18,6),
    high DECIMAL(18,6),
    low DECIMAL(18,6),
    close DECIMAL(18,6),
    volume BIGINT,
    created_at TIMESTAMP,
    PRIMARY KEY (token, timestamp)
)

-- Real-time Market Data Table
CREATE TABLE realtime_market_data (
    exchange VARCHAR,
    trading_symbol VARCHAR,
    symbol_token VARCHAR,
    ltp DECIMAL(18,6),
    open DECIMAL(18,6),
    high DECIMAL(18,6),
    low DECIMAL(18,6),
    close DECIMAL(18,6),
    last_trade_qty INTEGER,
    exch_feed_time TIMESTAMP,
    exch_trade_time TIMESTAMP,
    net_change DECIMAL(18,6),
    percent_change DECIMAL(18,6),
    avg_price DECIMAL(18,6),
    trade_volume BIGINT,
    opn_interest BIGINT,
    lower_circuit DECIMAL(18,6),
    upper_circuit DECIMAL(18,6),
    tot_buy_quan BIGINT,
    tot_sell_quan BIGINT,
    week_low_52 DECIMAL(18,6),
    week_high_52 DECIMAL(18,6),
    depth_json TEXT,
    timestamp TIMESTAMP,
    PRIMARY KEY (symbol_token, timestamp)
)

-- Technical Indicators Summary Table
CREATE TABLE technical_indicators_summary (
    token VARCHAR,
    symbol VARCHAR,
    name VARCHAR,
    date DATE,
    sma_50 DECIMAL(18,6),
    sma_100 DECIMAL(18,6),
    sma_200 DECIMAL(18,6),
    ema_20 DECIMAL(18,6),
    ema_50 DECIMAL(18,6),
    ema_200 DECIMAL(18,6),
    rsi_14 DECIMAL(18,6),
    rsi_21 DECIMAL(18,6),
    volatility_21 DECIMAL(18,6),
    volatility_200 DECIMAL(18,6),
    created_at TIMESTAMP,
    PRIMARY KEY (token, date)
)

-- Market Summary View
CREATE VIEW market_summary_view AS
SELECT
    -- Market data fields
    e.token,
    e.symbol,
    e.name,
    r.ltp,
    r.percent_change,
    r.trade_volume AS volume,
    r.week_low_52,
    r.week_high_52,
    -- Futures data
    f.ltp AS futures_ltp,
    f.opn_interest AS futures_oi,
    -- Technical indicators
    t.sma_50,
    t.sma_200,
    t.ema_20,
    t.rsi_14,
    t.volatility_21,
    -- Derived technical metrics
    CASE
        WHEN r.ltp > t.sma_200 THEN 'ABOVE_SMA200'
        WHEN r.ltp < t.sma_200 THEN 'BELOW_SMA200'
        ELSE 'AT_SMA200'
    END AS sma_200_position,
    CASE
        WHEN t.sma_50 > t.sma_200 THEN 'BULLISH_CROSSOVER'
        ELSE 'BEARISH_CROSSOVER'
    END AS ma_crossover_status,
    CASE
        WHEN t.sma_200 > 0 THEN ((r.ltp - t.sma_200) / t.sma_200) * 100
        ELSE 0
    END AS sma_200_percent_diff
FROM
    token_master e
LEFT JOIN
    realtime_market_data r ON e.token = r.symbol_token
LEFT JOIN
    realtime_market_data f ON e.futures_token = f.symbol_token
LEFT JOIN
    technical_indicators_summary t ON e.token = t.token
WHERE
    e.token_type = 'EQUITY'
    AND r.timestamp = (SELECT MAX(timestamp) FROM realtime_market_data)
```

## API Access

The system provides a FastAPI-based RESTful API for accessing market data:

### Starting the API Server

```bash
# Start the API server with default settings (localhost:8000)
python scripts/run_api_server.py

# Specify a different host and port
python scripts/run_api_server.py --host 0.0.0.0 --port 8080

# Enable auto-reload for development (automatically restart on code changes)
python scripts/run_api_server.py --reload
```

### API Endpoints

Once running, the API provides the following endpoints:

- **GET /api/market-summary**: Get market summary data for all symbols (includes technical indicators)
- **GET /api/market-summary/{symbol}**: Get market summary for a specific symbol
- **GET /api/market-summary/filter**: Filter market summary by price and change criteria
- **GET /api/market-summary/technical-filter**: Filter market data based on technical indicators
  - Query parameters:
    - `sma_position`: Filter by position relative to SMA200 (ABOVE_SMA200, BELOW_SMA200)
    - `crossover_status`: Filter by crossover status (BULLISH_CROSSOVER, BEARISH_CROSSOVER)
    - `min_rsi` / `max_rsi`: Filter by RSI-14 range
    - `min_volatility` / `max_volatility`: Filter by volatility range

### API Documentation

The API includes Swagger and ReDoc documentation:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

### Example API Usage in Frontend Code

#### Using JavaScript Fetch API

```javascript
// Get all market summary data
async function getAllMarketData() {
  try {
    const response = await fetch('http://localhost:8000/api/market-summary');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching market data:', error);
    return [];
  }
}

// Filter market data by technical indicators
async function filterByTechnicals(filters) {
  try {
    const params = new URLSearchParams();
    
    if (filters.smaPosition) params.append('sma_position', filters.smaPosition);
    if (filters.crossoverStatus) params.append('crossover_status', filters.crossoverStatus);
    if (filters.minRsi) params.append('min_rsi', filters.minRsi);
    if (filters.maxRsi) params.append('max_rsi', filters.maxRsi);
    
    const url = `http://localhost:8000/api/market-summary/technical-filter?${params.toString()}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error filtering by technicals:', error);
    return [];
  }
}
```

### Response Format

The API returns data in JSON format. Here's an example of the response structure including technical indicators:

```json
[
  {
    "token": "256265",
    "symbol": "RELIANCE",
    "name": "RELIANCE INDUSTRIES",
    "ltp": 2345.65,
    "percent_change": 1.25,
    "volume": 2500000,
    "week_low_52": 2100.00,
    "week_high_52": 2500.00,
    "futures_ltp": 2350.80,
    "futures_oi": 75000,
    
    "sma_50": 2320.50,
    "sma_200": 2200.30,
    "ema_20": 2330.25,
    "rsi_14": 65.3,
    "volatility_21": 32.5,
    
    "sma_200_position": "ABOVE_SMA200",
    "ma_crossover_status": "BULLISH_CROSSOVER",
    "sma_200_percent_diff": 6.61
  }
]
```

## Project Structure

```
├── api/                - FastAPI module for data access
│   ├── __init__.py     - Package initialization
│   ├── db.py           - Database access functions
│   ├── main.py         - API app initialization
│   ├── models.py       - Pydantic data models
│   ├── routes.py       - API route definitions
│   └── API_SPECIFICATION.md - API documentation
├── config/             - Application configuration
│   └── config.yaml     - Main configuration file
├── exports/            - Generated Parquet files for API consumption
├── logs/               - Generated log files 
├── scripts/            - Executable scripts
│   ├── fetch_all_equity_data.py - Batch equity data processing
│   ├── run_api_server.py        - API server launcher
│   └── realtime_market_monitor.py - Real-time market monitor
├── sqls/               - SQL queries and view definitions
│   ├── market_summary_view.sql  - Market summary view definition
│   └── technical_indicators_views.sql - Technical indicators views
├── src/                - Core source code modules
│   ├── angel_one_connector.py     - Connection to Angel One API
│   ├── config_manager.py          - Configuration management
│   ├── db_manager.py              - DuckDB operations handler
│   ├── equity_market_data_manager.py - Equity market data processing
│   ├── realtime_market_data_manager.py - Real-time market data processing
│   ├── technical_indicators_manager.py - Technical indicators calculation
│   └── token_manager.py            - Token processing logic
├── utils/              - Utility functions and scripts
│   ├── db_utility.py              - Database management tool
│   ├── export_market_summary.py   - Market summary exporter
│   └── reset_for_testing.py       - Testing reset utility
├── .env                - Environment variables (not tracked)
├── market_data_pipeline.py - Main data pipeline script
├── nfo_derivatives_hub.duckdb - Default database file
├── README.md           - Project documentation
└── requirements.txt    - Project dependencies
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
