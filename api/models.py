"""
Pydantic models for API responses.
"""
from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field

class MarketSummary(BaseModel):
    """Market summary data model."""
    token: str = Field(..., description="Unique token identifier")
    symbol: str = Field(..., description="Stock symbol")
    name: str = Field(..., description="Company name")
    futures_token: Optional[str] = Field(None, description="Reference to futures token")
    lotsize: Optional[int] = Field(None, description="Lot size for derivatives")
    expiry: Optional[date] = Field(None, description="Expiry date for futures")
    ltp: Optional[float] = Field(None, description="Last traded price")
    percent_change: Optional[float] = Field(None, description="Percentage change")
    open: Optional[float] = Field(None, description="Opening price")
    high: Optional[float] = Field(None, description="Highest price")
    low: Optional[float] = Field(None, description="Lowest price")
    close: Optional[float] = Field(None, description="Closing price")
    volume: Optional[int] = Field(None, description="Trading volume")
    opn_interest: Optional[int] = Field(None, description="Open interest")
    week_low_52: Optional[float] = Field(None, description="52-week low price")
    week_high_52: Optional[float] = Field(None, description="52-week high price")
    futures_ltp: Optional[float] = Field(None, description="Futures last traded price")
    futures_percent_change: Optional[float] = Field(None, description="Futures percentage change")
    futures_volume: Optional[int] = Field(None, description="Futures trading volume")
    futures_oi: Optional[int] = Field(None, description="Futures open interest")
    atm_price: Optional[float] = Field(None, description="At-the-money options price")
    atm_price_per_lot: Optional[float] = Field(None, description="At-the-money options price per lot")
    position_metric: Optional[float] = Field(None, description="Position metric (relative to 52-week range)")
    
    # Technical indicators
    sma_50: Optional[float] = Field(None, description="50-day Simple Moving Average")
    sma_100: Optional[float] = Field(None, description="100-day Simple Moving Average")
    sma_200: Optional[float] = Field(None, description="200-day Simple Moving Average")
    ema_20: Optional[float] = Field(None, description="20-day Exponential Moving Average")
    ema_50: Optional[float] = Field(None, description="50-day Exponential Moving Average")
    ema_200: Optional[float] = Field(None, description="200-day Exponential Moving Average")
    rsi_14: Optional[float] = Field(None, description="14-day Relative Strength Index")
    rsi_21: Optional[float] = Field(None, description="21-day Relative Strength Index")
    volatility_21: Optional[float] = Field(None, description="21-day Historical Volatility (annualized)")
    volatility_200: Optional[float] = Field(None, description="200-day Historical Volatility (annualized)")
    
    # Technical indicator derived metrics
    sma_200_position: Optional[str] = Field(None, description="Position relative to 200-day SMA (ABOVE_SMA200, BELOW_SMA200, AT_SMA200)")
    ma_crossover_status: Optional[str] = Field(None, description="MA crossover status (BULLISH_CROSSOVER, BEARISH_CROSSOVER, NEUTRAL)")
    sma_200_percent_diff: Optional[float] = Field(None, description="Percentage difference between current price and 200-day SMA")
    
    class Config:
        """Pydantic config."""
        orm_mode = True
        schema_extra = {
            "example": {
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
                "position_metric": 52.50,
                "sma_50": 2320.50,
                "sma_100": 2290.75,
                "sma_200": 2200.30,
                "ema_20": 2330.25,
                "ema_50": 2315.80,
                "ema_200": 2195.40,
                "rsi_14": 65.3,
                "rsi_21": 58.7,
                "volatility_21": 0.18,
                "volatility_200": 0.22,
                "sma_200_position": "AT_SMA200",
                "ma_crossover_status": "BULLISH_CROSSOVER",
                "sma_200_percent_diff": 0.05
            }
        }

class TechnicalIndicatorsSummary(BaseModel):
    """Technical indicators summary in wide format (one row per stock)."""
    token: str = Field(..., description="Unique token identifier")
    symbol_name: str = Field(..., description="Stock symbol name")
    trade_date: date = Field(..., description="Date of the latest trading data")
    sma_50: Optional[float] = Field(None, description="50-day Simple Moving Average")
    sma_100: Optional[float] = Field(None, description="100-day Simple Moving Average")
    sma_200: Optional[float] = Field(None, description="200-day Simple Moving Average")
    ema_20: Optional[float] = Field(None, description="20-day Exponential Moving Average")
    ema_50: Optional[float] = Field(None, description="50-day Exponential Moving Average")
    ema_200: Optional[float] = Field(None, description="200-day Exponential Moving Average")
    rsi_14: Optional[float] = Field(None, description="14-day Relative Strength Index")
    rsi_21: Optional[float] = Field(None, description="21-day Relative Strength Index")
    volatility_21: Optional[float] = Field(None, description="21-day Historical Volatility (annualized)")
    volatility_200: Optional[float] = Field(None, description="200-day Historical Volatility (annualized)")
    last_close: Optional[float] = Field(None, description="Last closing price")
    last_volume: Optional[int] = Field(None, description="Last trading volume")
    
    class Config:
        """Pydantic config."""
        orm_mode = True
        schema_extra = {
            "example": {
                "token": "256265",
                "symbol_name": "RELIANCE INDUSTRIES",
                "trade_date": "2025-03-15",
                "sma_50": 2320.50,
                "sma_100": 2290.75,
                "sma_200": 2200.30,
                "ema_20": 2330.25,
                "ema_50": 2315.80,
                "ema_200": 2195.40,
                "rsi_14": 65.3,
                "rsi_21": 58.7,
                "volatility_21": 0.18,
                "volatility_200": 0.22,
                "last_close": 2345.65,
                "last_volume": 2500000
            }
        } 