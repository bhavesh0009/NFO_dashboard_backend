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
                "position_metric": 52.50
            }
        } 