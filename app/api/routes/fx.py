"""
Foreign Exchange (FX) API routes.

Endpoints for:
- Currency conversion
- Exchange rate lookup
- Supported currencies
"""

from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.models.user import User
from app.services.fx import fx_service, CurrencyInfo


router = APIRouter(prefix="/fx", tags=["forex"])


# ============================================================================
# Schemas
# ============================================================================

class CurrencyResponse(BaseModel):
    """Currency information."""
    
    code: str
    name: str
    symbol: str
    decimal_places: int


class ConvertRequest(BaseModel):
    """Currency conversion request."""
    
    amount: Decimal = Field(..., gt=0, description="Amount to convert")
    from_currency: str = Field(..., min_length=3, max_length=3, description="Source currency code")
    to_currency: str = Field(..., min_length=3, max_length=3, description="Target currency code")


class ConvertResponse(BaseModel):
    """Currency conversion result."""
    
    original_amount: Decimal
    converted_amount: Decimal
    from_currency: str
    to_currency: str
    rate: float
    timestamp: str


class RatesResponse(BaseModel):
    """Exchange rates response."""
    
    base: str
    rates: dict
    timestamp: str
    cached: bool


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/currencies", summary="List supported currencies")
def list_currencies() -> dict:
    """Get list of all supported currencies."""
    currencies = CurrencyInfo.list_all()
    return {
        "currencies": currencies,
        "count": len(currencies),
    }


@router.get("/currencies/{code}", response_model=CurrencyResponse, summary="Get currency info")
def get_currency(code: str) -> CurrencyResponse:
    """Get information about a specific currency."""
    info = CurrencyInfo.get_info(code)
    
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Currency not found: {code}",
        )
    
    return CurrencyResponse(
        code=code.upper(),
        name=info["name"],
        symbol=info["symbol"],
        decimal_places=info["decimal_places"],
    )


@router.get("/rates", summary="Get exchange rates")
async def get_rates(
    base: str = Query("USD", min_length=3, max_length=3, description="Base currency"),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Get current exchange rates for a base currency.
    
    Rates are cached for 1 hour to stay within API limits.
    """
    if not CurrencyInfo.is_supported(base):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported base currency: {base}",
        )
    
    result = await fx_service.get_all_rates(base)
    
    if not result["rates"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Exchange rates temporarily unavailable. Please try again later.",
        )
    
    return result


@router.get("/rate", summary="Get exchange rate")
async def get_rate(
    from_currency: str = Query(..., alias="from", min_length=3, max_length=3),
    to_currency: str = Query(..., alias="to", min_length=3, max_length=3),
    user: User = Depends(get_current_user),
) -> dict:
    """Get the exchange rate between two currencies."""
    rate = await fx_service.get_rate(from_currency, to_currency)
    
    if rate is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch exchange rate. Please try again later.",
        )
    
    return {
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "rate": rate,
    }


@router.post("/convert", response_model=ConvertResponse, summary="Convert currency")
async def convert_currency(
    request: ConvertRequest,
    user: User = Depends(get_current_user),
) -> ConvertResponse:
    """
    Convert an amount from one currency to another.
    
    Uses real-time exchange rates.
    """
    result = await fx_service.convert(
        amount=request.amount,
        from_currency=request.from_currency,
        to_currency=request.to_currency,
    )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Currency conversion temporarily unavailable. Please try again later.",
        )
    
    return ConvertResponse(
        original_amount=result["original_amount"],
        converted_amount=result["converted_amount"],
        from_currency=result["from_currency"],
        to_currency=result["to_currency"],
        rate=result["rate"],
        timestamp=result["timestamp"],
    )


@router.get("/convert", summary="Convert currency (GET)")
async def convert_currency_get(
    amount: Decimal = Query(..., gt=0, description="Amount to convert"),
    from_currency: str = Query(..., alias="from", min_length=3, max_length=3),
    to_currency: str = Query(..., alias="to", min_length=3, max_length=3),
    user: User = Depends(get_current_user),
) -> dict:
    """
    Convert an amount from one currency to another (GET version).
    
    Convenience endpoint for simple conversions.
    """
    result = await fx_service.convert(
        amount=amount,
        from_currency=from_currency,
        to_currency=to_currency,
    )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Currency conversion temporarily unavailable.",
        )
    
    # Format with symbols
    from_info = CurrencyInfo.get_info(from_currency)
    to_info = CurrencyInfo.get_info(to_currency)
    
    from_symbol = from_info["symbol"] if from_info else ""
    to_symbol = to_info["symbol"] if to_info else ""
    
    return {
        "original": f"{from_symbol}{result['original_amount']} {result['from_currency']}",
        "converted": f"{to_symbol}{result['converted_amount']} {result['to_currency']}",
        "rate": result["rate"],
        "rate_display": f"1 {result['from_currency']} = {result['rate']:.4f} {result['to_currency']}",
    }
