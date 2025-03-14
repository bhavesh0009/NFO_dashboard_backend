# Angel One Data Pipeline

_Last Updated: March 12, 2025_

## Overview

This project extracts data from Angel One API and stores it in DuckDB for analysis and reporting. It provides a reliable data pipeline for financial market data.

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

## Usage

```bash
# Test equity market data fetch (without storing)
python main.py equity --limit 5 --verbose

# Test with storing data for 10 tokens
python main.py equity --limit 10 --store --verbose

# Process with ONE_MINUTE interval instead of default ONE_DAY
python main.py equity --limit 5 --interval ONE_MINUTE --verbose

# Process all equity tokens in batches
python main.py batch

# Process with custom batch size and limit
python main.py batch --batch-size 10 --limit 50

# Process with custom interval (ONE_MINUTE, FIVE_MINUTE, etc.)
python main.py batch --batch-size 10 --limit 50 --interval ONE_HOUR

# Test connection to Angel One API
python main.py connection

# Process and store tokens
python main.py tokens

# Fetch real-time market data for equity and futures
python main.py realtime

# Fetch real-time market data for equity only (no futures)
python main.py realtime --no-futures

# Fetch real-time market data with options included
python main.py realtime --options

# Fetch real-time market data with limits
python main.py realtime --equity-limit 10 --futures-limit 10

# Fetch real-time market data with ATM options only (default behavior with options)
python main.py realtime --options

# Fetch real-time market data with options and specify 2 strikes above and below ATM
python main.py realtime --options --strike-buffer 2

# Fetch real-time market data with exact ATM options only (1 call and 1 put per future)
python main.py realtime --options --exact-atm

# Fetch all options (not just ATM)
python main.py realtime --options --all-options

# Run continuous real-time market monitor
python scripts/realtime_market_monitor.py

# Run continuous monitor with custom refresh interval (30 seconds)
python scripts/realtime_market_monitor.py --refresh 30

# Run continuous monitor for equity only
python scripts/realtime_market_monitor.py --no-futures

# Run continuous monitor with ATM options only
python scripts/realtime_market_monitor.py --options

# Run continuous monitor with exact ATM options only (1 call and 1 put per future)
python scripts/realtime_market_monitor.py --options --exact-atm

# Run continuous monitor with all options (not just ATM)
python scripts/realtime_market_monitor.py --options --all-options

# Run continuous monitor with options and specify 3 strikes above and below ATM
python scripts/realtime_market_monitor.py --options --strike-buffer 3

# Run all basic tests
python main.py

# Complete Market Data Pipeline
# Run the complete pipeline with default settings (starts at any time, waits for market open)
python market_data_pipeline.py

# Run pipeline with options for ATM options only
python market_data_pipeline.py --options --exact-atm

# Skip token refresh and historical data steps
python market_data_pipeline.py --no-tokens --no-history

# Skip waiting for market open (for testing)
python market_data_pipeline.py --no-wait

# Run with custom refresh interval (30 seconds)
python market_data_pipeline.py --refresh 30

# Run with limited number of tokens
python market_data_pipeline.py --equity-limit 50 --futures-limit 50

# Export market summary to Parquet manually
python utils/export_market_summary.py

# Export market summary with custom output path
python utils/export_market_summary.py --output path/to/output.parquet

# Export market summary with custom SQL query
python utils/export_market_summary.py --sql path/to/query.sql
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

### ATM Options Processing

A key feature of the system is the ability to intelligently filter options to only include At-The-Money (ATM) and near-ATM strikes:

1. **Two-Pass Processing**:
   - First fetches futures data to determine current market prices
   - Then selectively fetches only relevant ATM options based on those prices
   - Significantly reduces API requests and database storage requirements

2. **Configurable Strike Buffer**:
   - Default includes 1 strike above and below ATM for each underlying
   - Customizable via `--strike-buffer` parameter (e.g., `--strike-buffer 2` for 2 strikes)
   - Enables precise control over the range of strikes to monitor

3. **Exact ATM Mode**:
   - Optional `--exact-atm` flag selects only the single closest strike to the ATM price for each underlying
   - Results in exactly 2 options per future (1 call and 1 put at the exact ATM strike)
   - Produces minimal dataset for focused ATM-only analysis

4. **Strike Distance Awareness**:
   - Automatically determines appropriate strike distances for each stock
   - Uses stored `strike_distance` values from token database
   - Falls back to sensible defaults when data unavailable (e.g., 50 for NIFTY, 100 for BANKNIFTY)

5. **Performance Benefits**:
   - Reduces options tokens processed by 90-95% compared to full options chain
   - Minimizes API rate limit consumption and database storage requirements
   - Maintains focus on the most relevant options for trading

This focused approach to options data collection provides several advantages:

- More efficient API usage
- Reduced database storage requirements
- Faster processing times
- Emphasis on the most relevant trading instruments

## Database Schema

The system uses three primary tables:

```sql
-- Token Master Table
CREATE TABLE IF NOT EXISTS token_master (
    token VARCHAR,
    symbol VARCHAR,
    name VARCHAR,
    expiry DATE,
    strike DECIMAL(18,6),
    lotsize INTEGER,
    instrumenttype VARCHAR,
    exch_seg VARCHAR,
    tick_size DECIMAL(18,6),
    token_type VARCHAR,  -- 'FUTURES', 'OPTIONS', or 'EQUITY'
    futures_token VARCHAR,
    strike_distance DECIMAL(18,6),  -- Distance between adjacent strikes for options
    created_at TIMESTAMP,
    PRIMARY KEY (token)
)

-- Historical Data Table
CREATE TABLE IF NOT EXISTS historical_data (
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
CREATE TABLE IF NOT EXISTS realtime_market_data (
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
```

## Options Analytics

The system includes advanced options analytics capabilities:

1. **Strike Price Normalization**:
   - Automatically adjusts strike prices by dividing by 100 to match market representation
   - Converts raw API values to actual market strikes (e.g., 800000 → 8000)
   - Ensures accurate and readable strike values for analysis

2. **Strike Distance Calculation**:
   - Automatically calculates standard strike distance for each stock
   - Uses mode calculation of differences between adjacent sorted strikes
   - Provides precise strike increments for option chain analysis
   - Enables accurate strike grid mapping for strategy development

Example strike distances for popular stocks:

- NIFTY: 50 points
- BANKNIFTY: 100 points
- AARTIIND: 5 points
- HDFC: 20 points
- RELIANCE: 10 points

These features enable more accurate options analytics and strategy development by providing normalized data that matches market conventions.

## Troubleshooting

### Unicode Errors in Windows Console

If you encounter Unicode encoding errors in the Windows console:

```
UnicodeEncodeError: 'charmap' codec can't encode character '\u274c' in position 29: character maps to <undefined>
```

The system includes automatic ASCII-compatible logging to address this issue. If you're extending the code, use the `setup_console_logging()` function in your scripts to ensure compatibility:

```python
from scripts.realtime_market_monitor import setup_console_logging

# Setup console logging at the beginning of your script
setup_console_logging()
```

### API Rate Limiting

If you encounter rate limit errors from the Angel One API:

- The real-time market data system respects the 1 request per second limit
- For batch processing, consider increasing the `request_delay` and `batch_delay` in the configuration
- For continuous monitoring, increase the `refresh_interval` in the command-line arguments

## Project Structure

```
├── config/
│   └── config.yaml          - Application configuration
├── src/
│   ├── angel_one_connector.py - Connection to Angel One API
│   ├── config_manager.py    - Configuration management
│   ├── db_manager.py        - DuckDB operations handler
│   ├── equity_market_data_manager.py - Equity market data processing
│   ├── realtime_market_data_manager.py - Real-time market data processing
│   ├── token_manager.py     - Token processing logic
│   └── __pycache__/         - Python cache files
├── scripts/
│   ├── fetch_all_equity_data.py - Batch equity market data processing
│   └── realtime_market_monitor.py - Continuous real-time market data monitoring
├── utils/
│   ├── db_utility.py        - Database management tool
│   ├── reset_for_testing.py - Testing reset utility
│   ├── truncate_db.py       - Database truncation utility
│   └── export_market_summary.py - Market summary Parquet exporter
├── logs/                    - Generated log files directory
├── db_backups/              - Generated database backups
├── exports/                 - Generated Parquet files for API
├── api/                     - FastAPI module for data access
├── sqls/                    - SQL queries and view definitions
├── main.py                  - Application entry point
├── .env                     - Environment variables (not tracked)
├── nfo_derivatives_hub.duckdb - Default database file
├── README.md                - Project documentation
├── DEVELOPMENT_LOG.md       - Development progress tracking
└── requirements.txt         - Project dependencies
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Market Data Pipeline

The system includes a comprehensive orchestration script (`market_data_pipeline.py`) that automates the entire data workflow:

1. **Token Refresh**: Automatically refreshes token master data if needed
2. **Historical Data Refresh**: Updates historical price data for equity tokens
3. **Market Hours Awareness**: Waits for market open if started before trading hours
4. **Real-time Monitoring**: Runs continuous real-time market data collection at specified intervals
5. **Data Export**: Exports market summary to Parquet files after each data refresh for API consumption

### Pipeline Workflow

The pipeline follows a sequential workflow:

```
Start → Token Refresh → Historical Data → Wait for Market Open → Real-time Monitoring (with Parquet exports each iteration)
```

Each step handles error conditions gracefully and continues to the next step even if a previous step had errors.

### Command-Line Options

The pipeline accepts various command-line options to customize its behavior:

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

Add the following entry to your crontab:

```
55 8 * * 1-5 cd /path/to/project && /path/to/python market_data_pipeline.py --options --exact-atm
```

This runs the script at 8:55 AM on weekdays (Monday-Friday).

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

- **GET /api/market-summary**: Get market summary data for all symbols
- **GET /api/market-summary/{symbol}**: Get market summary for a specific symbol
- **GET /api/market-summary/filter**: Filter market summary by various criteria
  - Query parameters:
    - `min_ltp`: Minimum Last Traded Price
    - `max_ltp`: Maximum Last Traded Price
    - `min_percent_change`: Minimum percentage change
    - `max_percent_change`: Maximum percentage change

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

// Get data for a specific symbol
async function getSymbolData(symbol) {
  try {
    const response = await fetch(`http://localhost:8000/api/market-summary/${symbol}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    const data = await response.json();
    return data;
  } catch (error) {
    console.error(`Error fetching data for ${symbol}:`, error);
    return null;
  }
}

// Filter market data
async function filterMarketData(filters) {
  try {
    const params = new URLSearchParams();
    
    if (filters.minLtp) params.append('min_ltp', filters.minLtp);
    if (filters.maxLtp) params.append('max_ltp', filters.maxLtp);
    if (filters.minPercentChange) params.append('min_percent_change', filters.minPercentChange);
    if (filters.maxPercentChange) params.append('max_percent_change', filters.maxPercentChange);
    
    const url = `http://localhost:8000/api/market-summary/filter?${params.toString()}`;
    const response = await fetch(url);
    
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error filtering market data:', error);
    return [];
  }
}
```

### Response Format

The API returns data in JSON format. Here's an example of the response structure:

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
    "position_metric": 52.50
  }
]
```
