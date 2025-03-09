# Angel One Data Pipeline

_Last Updated: March 9, 2025_

## Overview

This project extracts data from Angel One API and stores it in DuckDB for analysis and reporting. It provides a reliable data pipeline for financial market data.

## Features

- ✅ Secure connection to Angel One API
- ✅ Data extraction for various financial instruments
- ✅ Token values storage (master stock records)
  - Futures & Options (F&O) token processing
  - Equity spot token mapping
  - Automatic expiry date handling
- ✅ Efficient storage in DuckDB database
  - Unified schema for all token types
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
   pip install -r requirements.txt
   ```

4. Configure your Angel One API credentials (see Configuration section)

## Configuration

Create a `.env` file in the project root with the following variables:

```
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_PIN=your_pin
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

The pipeline handles two main types of financial instruments in a unified storage system:

1. **Futures Tokens**
   - Filters FUTSTK instruments from NFO segment
   - Automatically identifies current expiry contracts
   - Processes expiry dates into standardized format
   - Handles numeric data validation

2. **Equity Tokens**
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
    strike DECIMAL(18,6),
    lotsize INTEGER,
    instrumenttype VARCHAR,
    exch_seg VARCHAR,
    tick_size DECIMAL(18,6),
    token_type VARCHAR,  -- 'FUTURES' or 'EQUITY'
    futures_token VARCHAR,  -- Reference to futures token for equity
    created_at TIMESTAMP,
    PRIMARY KEY (token)
)
```

## Project Structure

```
├── src/
│   ├── angel_one_connector.py - Connection to Angel One API
│   ├── db_manager.py - DuckDB operations handler
│   └── ...
├── main.py - Application entry point and testing script
├── .env - Environment variables (not tracked in git)
├── README.md - Project documentation
├── DEVELOPMENT_LOG.md - Development progress tracking
└── requirements.txt - Project dependencies
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
