# Angel One Data Pipeline

## Overview

This project extracts data from Angel One API and stores it in DuckDB for analysis and reporting. It provides a reliable data pipeline for financial market data.

## Features

- Secure connection to Angel One API
- Data extraction for various financial instruments
- Token values storage (master stock records)
- Efficient storage in DuckDB database
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
from src.angel_one_connector import AngelOneConnector

# Initialize connector
connector = AngelOneConnector()

# Connect to API
if connector.connect():
    # Fetch and store token values
    tokens = connector.get_tokens()
    
    # Work with the data
    print(f"Retrieved {len(tokens)} tokens")
```

## Project Structure

```
├── src/
│   ├── angel_one_connector.py - Connection to Angel One API
│   ├── db_manager.py - DuckDB operations handler
│   └── ...
├── .env - Environment variables (not tracked in git)
├── README.md - Project documentation
├── DEVELOPMENT_LOG.md - Development progress tracking
└── requirements.txt - Project dependencies
```

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
