"""
API routes for market data.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from api.db import get_market_summary, get_market_summary_for_symbol, filter_market_summary, get_technical_indicators_summary
from api.models import MarketSummary, TechnicalIndicatorsSummary
import pandas as pd

router = APIRouter(prefix="/api", tags=["market"])

@router.get("/market-summary", response_model=List[MarketSummary], summary="Get market summary data")
async def get_market_summary_route():
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
async def filter_market_summary_route(
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
async def get_technical_indicators_route():
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

@router.get("/market-summary/technical-filter", response_model=List[MarketSummary], summary="Filter market data by technical indicators")
async def filter_market_by_technicals(
    sma_position: Optional[str] = Query(None, description="Filter by position relative to SMA200 (ABOVE_SMA200, BELOW_SMA200, AT_SMA200)"),
    crossover_status: Optional[str] = Query(None, description="Filter by MA crossover status (BULLISH_CROSSOVER, BEARISH_CROSSOVER, NEUTRAL)"),
    min_rsi: Optional[float] = Query(None, description="Minimum RSI-14 value (0-100)"),
    max_rsi: Optional[float] = Query(None, description="Maximum RSI-14 value (0-100)"),
    min_volatility: Optional[float] = Query(None, description="Minimum 21-day volatility"),
    max_volatility: Optional[float] = Query(None, description="Maximum 21-day volatility")
):
    """
    Filter market data based on technical indicators.
    
    This endpoint allows filtering stocks based on various technical analysis criteria:
    
    - **SMA Position**: Filter stocks that are trading above or below their 200-day SMA
    - **Crossover Status**: Find stocks with bullish or bearish moving average crossovers
    - **RSI Range**: Filter stocks with RSI in specified range (e.g., oversold < 30, overbought > 70)
    - **Volatility Range**: Find stocks with specific volatility characteristics
    
    The response includes both market data and technical indicators in a single result.
    
    Args:
        sma_position: Position relative to 200-day SMA (ABOVE_SMA200, BELOW_SMA200, AT_SMA200)
        crossover_status: MA crossover status (BULLISH_CROSSOVER, BEARISH_CROSSOVER, NEUTRAL)
        min_rsi: Minimum RSI-14 value (0-100)
        max_rsi: Maximum RSI-14 value (0-100)
        min_volatility: Minimum 21-day volatility 
        max_volatility: Maximum 21-day volatility
        
    Returns:
        Filtered list of market summary records with technical indicators
    """
    # Get all market data
    data = get_market_summary()
    
    if not data:
        return []
    
    # Convert to DataFrame for easier filtering
    df = pd.DataFrame(data)
    
    # Apply filters based on technical indicators
    if sma_position:
        df = df[df['sma_200_position'] == sma_position]
        
    if crossover_status:
        df = df[df['ma_crossover_status'] == crossover_status]
        
    if min_rsi is not None:
        df = df[df['rsi_14'] >= min_rsi]
        
    if max_rsi is not None:
        df = df[df['rsi_14'] <= max_rsi]
        
    if min_volatility is not None:
        df = df[df['volatility_21'] >= min_volatility]
        
    if max_volatility is not None:
        df = df[df['volatility_21'] <= max_volatility]
    
    # Return filtered data
    return df.to_dict(orient='records') 