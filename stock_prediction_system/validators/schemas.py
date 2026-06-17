"""
Validation schemas using Pydantic for request validation.
Provides type-safe validation for API requests.
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, Literal
from enum import Enum


class FrequencyEnum(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class BuyRequest(BaseModel):
    """Validation schema for buy stock requests"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    quantity: int = Field(..., gt=0, description="Number of shares to buy")

    @validator('symbol')
    def symbol_must_be_valid(cls, v):
        v = v.strip().upper()
        if not v:
            raise ValueError('Symbol cannot be empty')
        if len(v) > 20:
            raise ValueError('Symbol too long')
        return v

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        if v > 1000000:
            raise ValueError('Quantity too large')
        return v


class SellRequest(BaseModel):
    """Validation schema for sell stock requests"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    quantity: int = Field(..., gt=0, description="Number of shares to sell")

    @validator('symbol')
    def symbol_must_be_valid(cls, v):
        v = v.strip().upper()
        if not v:
            raise ValueError('Symbol cannot be empty')
        return v

    @validator('quantity')
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be greater than 0')
        return v


class SIPCreateRequest(BaseModel):
    """Validation schema for SIP creation requests"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")
    amount: float = Field(..., gt=0, description="Amount per installment")
    frequency: FrequencyEnum = Field(default=FrequencyEnum.monthly, description="Payment frequency")
    duration_months: int = Field(..., ge=1, le=60, description="Duration in months")

    @validator('symbol')
    def symbol_must_be_valid(cls, v):
        v = v.strip().upper()
        if not v:
            raise ValueError('Symbol cannot be empty')
        return v

    @validator('amount')
    def amount_must_be_sufficient(cls, v):
        if v < 500:
            raise ValueError('Minimum SIP amount is ₹500')
        if v > 10000000:
            raise ValueError('Amount too large')
        return v


class SIPExecuteRequest(BaseModel):
    """Validation schema for SIP execution requests"""
    sip_id: Optional[int] = Field(None, description="Specific SIP ID to execute")


class WalletCreateRequest(BaseModel):
    """Validation schema for wallet creation"""
    username: Optional[str] = Field(None, max_length=100, description="Username")


class StockSymbolRequest(BaseModel):
    """Validation schema for stock symbol requests"""
    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol")

    @validator('symbol')
    def symbol_must_be_valid(cls, v):
        v = v.strip().upper()
        if not v:
            raise ValueError('Symbol cannot be empty')
        return v


class PaginationRequest(BaseModel):
    """Validation schema for pagination"""
    limit: int = Field(default=50, ge=1, le=100, description="Number of results")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")