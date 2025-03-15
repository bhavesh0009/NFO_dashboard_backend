#!/bin/bash
# Run technical indicators calculation with all configured indicators

# Log start
echo "Starting technical indicators calculation process..."
echo "Date: $(date)"
echo

# Set environment variables (if needed)
# export PYTHONPATH=.

# Run with all configured indicators
echo "Running fetch_all_equity_data.py with all configured indicators..."
python scripts/fetch_all_equity_data.py --all-indicators --limit 10 --verbose

# Check exit code
if [ $? -eq 0 ]; then
    echo
    echo "Technical indicators calculation completed successfully!"
else
    echo
    echo "Technical indicators calculation failed with exit code $?"
fi

echo "Date: $(date)"
echo "Done!" 