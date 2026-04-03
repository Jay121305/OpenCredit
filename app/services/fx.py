"""
Multi-Currency Foreign Exchange Service.

Uses ExchangeRate-API for real-time exchange rates.
https://exchangerate-api.com/
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, List, Any
from functools import lru_cache

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class CurrencyInfo:
    """Information about a supported currency."""
    
    CURRENCIES = {
        "USD": {"name": "US Dollar", "symbol": "$", "decimal_places": 2},
        "EUR": {"name": "Euro", "symbol": "€", "decimal_places": 2},
        "GBP": {"name": "British Pound", "symbol": "£", "decimal_places": 2},
        "JPY": {"name": "Japanese Yen", "symbol": "¥", "decimal_places": 0},
        "CAD": {"name": "Canadian Dollar", "symbol": "C$", "decimal_places": 2},
        "AUD": {"name": "Australian Dollar", "symbol": "A$", "decimal_places": 2},
        "CHF": {"name": "Swiss Franc", "symbol": "CHF", "decimal_places": 2},
        "CNY": {"name": "Chinese Yuan", "symbol": "¥", "decimal_places": 2},
        "INR": {"name": "Indian Rupee", "symbol": "₹", "decimal_places": 2},
        "MXN": {"name": "Mexican Peso", "symbol": "$", "decimal_places": 2},
        "BRL": {"name": "Brazilian Real", "symbol": "R$", "decimal_places": 2},
        "KRW": {"name": "South Korean Won", "symbol": "₩", "decimal_places": 0},
        "SGD": {"name": "Singapore Dollar", "symbol": "S$", "decimal_places": 2},
        "HKD": {"name": "Hong Kong Dollar", "symbol": "HK$", "decimal_places": 2},
        "SEK": {"name": "Swedish Krona", "symbol": "kr", "decimal_places": 2},
        "NOK": {"name": "Norwegian Krone", "symbol": "kr", "decimal_places": 2},
        "NZD": {"name": "New Zealand Dollar", "symbol": "NZ$", "decimal_places": 2},
        "ZAR": {"name": "South African Rand", "symbol": "R", "decimal_places": 2},
        "AED": {"name": "UAE Dirham", "symbol": "د.إ", "decimal_places": 2},
        "PHP": {"name": "Philippine Peso", "symbol": "₱", "decimal_places": 2},
    }
    
    @classmethod
    def get_info(cls, code: str) -> Optional[Dict[str, Any]]:
        """Get currency info by code."""
        return cls.CURRENCIES.get(code.upper())
    
    @classmethod
    def is_supported(cls, code: str) -> bool:
        """Check if currency is supported."""
        return code.upper() in cls.CURRENCIES
    
    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        """List all supported currencies."""
        return [
            {"code": code, **info}
            for code, info in cls.CURRENCIES.items()
        ]


class ExchangeRateService:
    """
    Exchange rate service using ExchangeRate-API.
    
    Features:
    - Real-time rates with caching
    - Currency conversion
    - Historical rates support (if API supports)
    - Fallback to cached rates on API failure
    """
    
    BASE_URL = "https://v6.exchangerate-api.com/v6"
    CACHE_DURATION = timedelta(hours=1)  # Cache rates for 1 hour
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.exchangerate_api_key
        self.rates_cache: Dict[str, Dict[str, float]] = {}
        self.cache_timestamp: Optional[datetime] = None
        self.base_currency = "USD"
    
    def _is_cache_valid(self) -> bool:
        """Check if cached rates are still valid."""
        if not self.cache_timestamp or not self.rates_cache:
            return False
        return datetime.utcnow() - self.cache_timestamp < self.CACHE_DURATION
    
    async def fetch_rates(self, base: str = "USD") -> Dict[str, float]:
        """
        Fetch current exchange rates from API.
        
        Args:
            base: Base currency code (default: USD)
            
        Returns:
            Dictionary of currency codes to exchange rates
        """
        if not self.api_key:
            logger.warning("No ExchangeRate API key configured")
            return {}
        
        # Check cache
        if self._is_cache_valid() and base.upper() in self.rates_cache:
            return self.rates_cache[base.upper()]
        
        try:
            url = f"{self.BASE_URL}/{self.api_key}/latest/{base.upper()}"
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                data = response.json()
            
            if data.get("result") != "success":
                logger.error(f"ExchangeRate API error: {data.get('error-type', 'Unknown')}")
                return self.rates_cache.get(base.upper(), {})
            
            rates = data.get("conversion_rates", {})
            
            # Update cache
            self.rates_cache[base.upper()] = rates
            self.cache_timestamp = datetime.utcnow()
            
            logger.info(f"Fetched {len(rates)} exchange rates for {base}")
            return rates
            
        except Exception as e:
            logger.error(f"Failed to fetch exchange rates: {e}")
            # Return cached rates if available
            return self.rates_cache.get(base.upper(), {})
    
    async def get_rate(self, from_currency: str, to_currency: str) -> Optional[float]:
        """
        Get exchange rate between two currencies.
        
        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            
        Returns:
            Exchange rate or None if unavailable
        """
        from_code = from_currency.upper()
        to_code = to_currency.upper()
        
        if from_code == to_code:
            return 1.0
        
        # Fetch rates with from_currency as base
        rates = await self.fetch_rates(from_code)
        
        if to_code in rates:
            return rates[to_code]
        
        # Try inverse calculation via USD
        if from_code != "USD":
            usd_rates = await self.fetch_rates("USD")
            if from_code in usd_rates and to_code in usd_rates:
                # Convert via USD
                # from_currency -> USD -> to_currency
                from_to_usd = 1 / usd_rates[from_code]
                usd_to_target = usd_rates[to_code]
                return from_to_usd * usd_to_target
        
        return None
    
    async def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        round_result: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Convert an amount from one currency to another.
        
        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            round_result: Whether to round to currency's decimal places
            
        Returns:
            {
                "original_amount": Decimal,
                "converted_amount": Decimal,
                "from_currency": str,
                "to_currency": str,
                "rate": float,
                "timestamp": str,
            }
        """
        rate = await self.get_rate(from_currency, to_currency)
        
        if rate is None:
            return None
        
        converted = amount * Decimal(str(rate))
        
        # Round to appropriate decimal places
        if round_result:
            target_info = CurrencyInfo.get_info(to_currency)
            if target_info:
                places = target_info.get("decimal_places", 2)
                converted = converted.quantize(
                    Decimal(10) ** -places,
                    rounding=ROUND_HALF_UP
                )
        
        return {
            "original_amount": amount,
            "converted_amount": converted,
            "from_currency": from_currency.upper(),
            "to_currency": to_currency.upper(),
            "rate": rate,
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    async def get_all_rates(self, base: str = "USD") -> Dict[str, Any]:
        """
        Get all exchange rates for a base currency.
        
        Returns:
            {
                "base": str,
                "rates": Dict[str, float],
                "timestamp": str,
            }
        """
        rates = await self.fetch_rates(base)
        
        return {
            "base": base.upper(),
            "rates": rates,
            "timestamp": datetime.utcnow().isoformat(),
            "cached": self._is_cache_valid(),
        }


# Singleton instance
fx_service = ExchangeRateService()
