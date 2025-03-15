"""
API routes for market data.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from api.db import get_market_summary, get_market_summary_for_symbol, filter_market_summary, get_technical_indicators_summary
from api.models import MarketSummary, TechnicalIndicatorsSummary

router = APIRouter(prefix="/api", tags=["market"])

@router.get("/market-summary", response_model=List[MarketSummary], summary="Get market summary data")
async def get_market_summary():
    """
    Get market summary data for all available symbols.
    
    Returns a list of market summary records with the latest data.
    """
    data = get_market_summary()
    if not data:
        return []
    return data

@router.get("/market-summary/{symbol}", response_model=List[MarketSummary], summary="Get market summary for a symbol")
async def get_market_summary_by_symbol(symbol: str):
    """
    Get market summary data for a specific symbol.
    
    Args:
        symbol: The symbol to get data for (case-insensitive, partial match)
        
    Returns:
        List of matching market summary records
    """
    data = get_market_summary(symbol=symbol)
    if not data:
        return []
    return data

@router.get("/market-summary/filter", response_model=List[MarketSummary], summary="Filter market summary data")
async def filter_market_summary(
    min_ltp: Optional[float] = Query(None, description="Minimum Last Traded Price"),
    max_ltp: Optional[float] = Query(None, description="Maximum Last Traded Price"),
    min_percent_change: Optional[float] = Query(None, description="Minimum percentage change"),
    max_percent_change: Optional[float] = Query(None, description="Maximum percentage change")
):
    """
    Filter market summary data based on criteria.
    
    Args:
        min_ltp: Minimum Last Traded Price
        max_ltp: Maximum Last Traded Price
        min_percent_change: Minimum percentage change
        max_percent_change: Maximum percentage change
        
    Returns:
        Filtered list of market summary records
    """
    data = filter_market_summary(
        min_ltp=min_ltp,
        max_ltp=max_ltp,
        min_percent_change=min_percent_change,
        max_percent_change=max_percent_change
    )
    if not data:
        return []
    return data

@router.get("/technical-indicators", response_model=List[TechnicalIndicatorsSummary], summary="Get technical indicators data")
async def get_technical_indicators():
    """
    Get technical indicators summary data for all available symbols.
    
    Returns:
        List of technical indicators summary records with the latest data
    """
    data = get_technical_indicators_summary()
    if not data:
        return []
    return data

@router.get("/technical-indicators/{symbol}", response_model=List[TechnicalIndicatorsSummary], summary="Get technical indicators for a symbol")
async def get_technical_indicators_by_symbol(symbol: str):
    """
    Get technical indicators summary data for a specific symbol.
    
    Args:
        symbol: The symbol to get data for (case-insensitive, partial match)
        
    Returns:
        List of matching technical indicators summary records
    """
    data = get_technical_indicators_summary(symbol=symbol)
    if not data:
        return []
    return data 