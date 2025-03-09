# Angel One Data Pipeline

_Last Updated: March 9, 2025_

## Overview

This project extracts data from Angel One API and stores it in DuckDB for analysis and reporting. It provides a reliable data pipeline for financial market data.

## Features

- ✅ **API Integration**: Secure Angel One API connection with token management
- ✅ **Token Management**: F&O and equity token handling with expiry management
- ✅ **Database Storage**: Efficient DuckDB storage with automated validation
- ✅ **Equity Market Data**: OHLCV data from 2000-present with multiple intervals
- ✅ **Process Automation**: Batched processing with rate limiting

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

# Additional configurations for token types, etc.
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

# Run all basic tests
python main.py
```

## Data Processing

The pipeline efficiently processes three instrument types:

- **Futures**: Current expiry contracts from NFO segment with standardized dates
- **Options**: Strike price validation with distribution analysis
- **Equity**: Spot token mapping with referential integrity to futures

## Database Schema

The system uses two primary tables:

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
    token_type VARCHAR,  -- 'FUTURES', 'OPTIONS', or 'EQUITY'
    futures_token VARCHAR,
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
```

## Project Structure

```
├── config/
│   └── config.yaml          - Application configuration
├── src/
│   ├── angel_one_connector.py - Connection to Angel One API
│   ├── config_manager.py    - Configuration management
│   ├── db_manager.py        - DuckDB operations handler
│   ├── equity_market_data_manager.py - Equity market data processing
│   ├── token_manager.py     - Token processing logic
│   └── __pycache__/         - Python cache files
├── scripts/
│   └── fetch_all_equity_data.py - Batch equity market data processing
├── utils/
│   ├── db_utility.py        - Database management tool
│   ├── reset_for_testing.py - Testing reset utility
│   └── truncate_db.py       - Database truncation utility
├── logs/                    - Generated log files directory
├── db_backups/              - Generated database backups
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