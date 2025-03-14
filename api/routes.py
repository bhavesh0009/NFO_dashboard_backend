"""
API routes for market data.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
from api.db import get_market_summary, get_market_summary_for_symbol
from api.models import MarketSummary

router = APIRouter(prefix="/api", tags=["market"])

@router.get("/market-summary", response_model=List[MarketSummary])
async def market_summary():
    """
    Get summary of market data for all symbols.
    
    Returns:
        List of market summary data
    """
    data = get_market_summary()
    return data

@router.get("/market-summary/{symbol}", response_model=MarketSummary)
async def market_summary_by_symbol(symbol: str):
    """
    Get summary of market data for a specific symbol.
    
    Args:
        symbol: The symbol to get data for
        
    Returns:
        Market summary data for the symbol
    """
    data = get_market_summary_for_symbol(symbol)
    if not data:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
    return data

@router.get("/market-summary/filter", response_model=List[MarketSummary])
async def market_summary_filter(
    min_ltp: Optional[float] = None,
    max_ltp: Optional[float] = None,
    min_percent_change: Optional[float] = None,
    max_percent_change: Optional[float] = None
):
    """
    Filter market summary data by various criteria.
    
    Args:
        min_ltp: Minimum Last Traded Price
        max_ltp: Maximum Last Traded Price
        min_percent_change: Minimum percentage change
        max_percent_change: Maximum percentage change
        
    Returns:
        Filtered list of market summary data
    """
    # Get all data first
    data = get_market_summary()
    
    # Apply filters
    filtered_data = data.copy()
    
    # Filter based on provided criteria
    if min_ltp is not None:
        filtered_data = [item for item in filtered_data if item.get('ltp') is not None and item.get('ltp') >= min_ltp]
        
    if max_ltp is not None:
        filtered_data = [item for item in filtered_data if item.get('ltp') is not None and item.get('ltp') <= max_ltp]
        
    if min_percent_change is not None:
        filtered_data = [item for item in filtered_data if item.get('percent_change') is not None and item.get('percent_change') >= min_percent_change]
        
    if max_percent_change is not None:
        filtered_data = [item for item in filtered_data if item.get('percent_change') is not None and item.get('percent_change') <= max_percent_change]
            
    return filtered_data 