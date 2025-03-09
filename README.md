# Angel One Data Pipeline

_Last Updated: March 9, 2025_

## Overview

This project extracts data from Angel One API and stores it in DuckDB for analysis and reporting. It provides a reliable data pipeline for financial market data.

## Features

- ✅ Secure connection to Angel One API
- ✅ Data extraction for various financial instruments
- ✅ Token values storage (master stock records)
  - Futures & Options (F&O) token processing
    - Current expiry futures contracts
    - Current expiry options with strike prices
  - Equity spot token mapping
  - Automatic expiry date handling
  - Strike price validation and distribution analysis
- ✅ Efficient storage in DuckDB database
  - Unified schema for all token types (futures, options, equity)
  - Smart token type differentiation
  - Automated data validation
  - Referential integrity between instruments
- Automated data refresh and synchronization

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

The database serves as a central hub for:

- Token master data (futures and equity)
- Historical price data
- Spot values for dashboard
- Market analytics and metrics

Access configuration values in code:

```python
from src.config_manager import config

# Get API URL
api_url = config.get('api', 'angel_one', 'token_master_url')

# Get market hours
market_start = config.get('market', 'trading_hours', 'start')
```

## Usage

```python
# Basic usage example
from src.token_manager import TokenManager
from src.db_manager import DBManager

# Initialize managers
db_manager = DBManager()
token_manager = TokenManager(db_manager)

# Fetch and process tokens
if token_manager.fetch_tokens():
    # Process and store both futures and equity tokens
    success = token_manager.process_and_store_tokens()
    print(f"Token processing {'successful' if success else 'failed'}")
```

## Data Processing

The pipeline handles three main types of financial instruments in a unified storage system:

1. **Futures Tokens**
   - Filters FUTSTK instruments from NFO segment
   - Automatically identifies current expiry contracts
   - Processes expiry dates into standardized format
   - Handles numeric data validation

2. **Options Tokens**
   - Filters OPTSTK instruments from NFO segment
   - Identifies current expiry contracts
   - Validates and processes strike prices
   - Provides strike price distribution analysis
   - Maintains standardized date formats

3. **Equity Tokens**
   - Maps futures to corresponding equity spot tokens
   - Maintains referential integrity with futures
   - Stores in normalized database structure
   - Automatic type conversion and validation

## Database Schema

The system uses a unified token master table with the following structure:

```sql
CREATE TABLE token_master (
    token VARCHAR,
    symbol VARCHAR,
    name VARCHAR,
    expiry DATE,
    strike DECIMAL(18,6),  -- Particularly important for options
    lotsize INTEGER,
    instrumenttype VARCHAR,
    exch_seg VARCHAR,
    tick_size DECIMAL(18,6),
    token_type VARCHAR,  -- 'FUTURES', 'OPTIONS', or 'EQUITY'
    futures_token VARCHAR,  -- Reference to futures token for equity
    created_at TIMESTAMP,
    PRIMARY KEY (token)
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
│   ├── token_manager.py     - Token processing logic
│   └── ...
├── main.py                  - Application entry point
├── .env                     - Environment variables (not tracked)
├── README.md               - Project documentation
├── DEVELOPMENT_LOG.md      - Development progress tracking
└── requirements.txt        - Project dependencies
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
