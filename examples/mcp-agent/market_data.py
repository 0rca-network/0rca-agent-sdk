"""
Market Data Service for MCP API integration.
Handles API requests, response parsing, and error handling.
"""

import requests
import logging
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from requests.exceptions import Timeout, RequestException

try:
    from .config import MCPConfig
    from .logging_config import get_logger
except ImportError:
    from config import MCPConfig
    from logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class MarketDataResponse:
    """Structured market data response"""
    symbol: str
    price: float
    timestamp: int
    market_depth: Dict[str, Any]
    volume_24h: float
    price_change_24h: float

class MCPAPIError(Exception):
    """Custom exception for MCP API errors"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class MarketDataService:
    """Service for interacting with MCP Market Data API"""
    
    def __init__(self, mcp_config: MCPConfig):
        self.config = mcp_config
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "mcp-market-data-agent/1.0"
        })
        
        if self.config.api_key:
            self.session.headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        logger.log_service_initialization("MarketDataService", True, {
            "endpoint": self.config.api_endpoint,
            "timeout": self.config.timeout_seconds,
            "retry_attempts": self.config.retry_attempts
        })
    
    def fetch_market_data(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Fetch market data from MCP API with retry logic.
        
        Args:
            symbols: List of symbols to fetch data for. If None, fetches default symbols.
            
        Returns:
            Dict containing market data for requested symbols
            
        Raises:
            MCPAPIError: If API request fails after retries
        """
        start_time = time.time()
        
        try:
            # Prepare request parameters
            params = {}
            if symbols:
                params['symbols'] = ','.join(symbols)
            
            request_details = {
                "endpoint": self.config.api_endpoint,
                "method": "GET",
                "symbols": symbols,
                "params": params
            }
            
            logger.logger.info(f"Fetching market data for symbols: {symbols or 'default'}")
            
            # Make API request with retry logic
            response_data = self._make_api_request_with_retry(params)
            
            # Validate response format
            self._validate_response_format(response_data)
            
            # Log successful API request
            response_time = int((time.time() - start_time) * 1000)
            logger.log_api_request(True, request_details, {
                "status_code": 200,
                "response_time_ms": response_time,
                "data_count": len(response_data)
            })
            
            return response_data
            
        except MCPAPIError as e:
            # Log API error with context
            response_time = int((time.time() - start_time) * 1000)
            logger.log_api_request(False, {
                "endpoint": self.config.api_endpoint,
                "method": "GET",
                "symbols": symbols
            }, None, {
                "type": "MCPAPIError",
                "message": e.message,
                "status_code": e.status_code
            })
            raise
        except Exception as e:
            # Log unexpected error
            response_time = int((time.time() - start_time) * 1000)
            logger.log_api_request(False, {
                "endpoint": self.config.api_endpoint,
                "method": "GET",
                "symbols": symbols
            }, None, {
                "type": "UnexpectedError",
                "message": str(e)
            })
            logger.log_error(e, {"operation": "fetch_market_data", "symbols": symbols})
            raise MCPAPIError(f"Market data fetch failed: {str(e)}")
    
    def _make_api_request_with_retry(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make API request with timeout and retry logic.
        
        Args:
            params: Request parameters
            
        Returns:
            Parsed JSON response data
            
        Raises:
            MCPAPIError: If request fails after all retries
        """
        last_exception = None
        attempts_made = 0
        
        for attempt in range(self.config.retry_attempts + 1):  # +1 for initial attempt
            attempts_made = attempt + 1
            request_start = time.time()
            
            try:
                logger.logger.debug(f"API request attempt {attempts_made}/{self.config.retry_attempts + 1}")
                
                response = self.session.get(
                    self.config.api_endpoint,
                    params=params,
                    timeout=self.config.timeout_seconds
                )
                
                response_time = int((time.time() - request_start) * 1000)
                
                # Handle API errors
                self.handle_api_errors(response)
                
                # Log successful request
                logger.log_api_request(True, {
                    "endpoint": self.config.api_endpoint,
                    "method": "GET",
                    "attempt": attempts_made
                }, {
                    "status_code": response.status_code,
                    "response_time_ms": response_time
                })
                
                # Parse and return response
                return response.json()
                
            except Timeout as e:
                last_exception = e
                response_time = int((time.time() - request_start) * 1000)
                
                logger.log_api_request(False, {
                    "endpoint": self.config.api_endpoint,
                    "method": "GET",
                    "attempt": attempts_made
                }, {
                    "response_time_ms": response_time
                }, {
                    "type": "Timeout",
                    "message": str(e)
                })
                
                # Don't retry on the last attempt
                if attempt < self.config.retry_attempts:
                    time.sleep(1)  # Brief delay before retry
                    continue
                    
            except MCPAPIError as e:
                # Log and re-raise MCPAPIError with preserved status code
                response_time = int((time.time() - request_start) * 1000)
                logger.log_api_request(False, {
                    "endpoint": self.config.api_endpoint,
                    "method": "GET",
                    "attempt": attempts_made
                }, {
                    "response_time_ms": response_time
                }, {
                    "type": "MCPAPIError",
                    "message": e.message,
                    "status_code": e.status_code
                })
                raise e
                
            except RequestException as e:
                last_exception = e
                response_time = int((time.time() - request_start) * 1000)
                
                logger.log_api_request(False, {
                    "endpoint": self.config.api_endpoint,
                    "method": "GET",
                    "attempt": attempts_made
                }, {
                    "response_time_ms": response_time
                }, {
                    "type": "RequestException",
                    "message": str(e)
                })
                
                # Don't retry on non-timeout network errors - break immediately
                break
                
            except Exception as e:
                last_exception = e
                response_time = int((time.time() - request_start) * 1000)
                
                logger.log_api_request(False, {
                    "endpoint": self.config.api_endpoint,
                    "method": "GET",
                    "attempt": attempts_made
                }, {
                    "response_time_ms": response_time
                }, {
                    "type": "UnexpectedError",
                    "message": str(e)
                })
                break
        
        # If we get here, all retries failed
        raise MCPAPIError(f"API request failed after {attempts_made} attempts: {last_exception}")
    
    def _validate_response_format(self, response_data: Dict[str, Any]) -> None:
        """
        Validate that the API response has the expected format.
        
        Args:
            response_data: The parsed JSON response from the API
            
        Raises:
            MCPAPIError: If response format is invalid
        """
        try:
            if not isinstance(response_data, dict):
                raise MCPAPIError("API response must be a dictionary")
            
            # Check if response contains market data
            if not response_data:
                logger.logger.warning("API returned empty response")
                return
            
            # Validate each symbol's data structure
            validation_errors = []
            for symbol, data in response_data.items():
                if not isinstance(data, dict):
                    validation_errors.append(f"Invalid data format for symbol {symbol}")
                    continue
                
                required_fields = ['symbol', 'price', 'timestamp']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    validation_errors.append(f"Missing required fields for {symbol}: {missing_fields}")
                    continue
                
                # Validate data types
                try:
                    float(data['price'])
                    int(data['timestamp'])
                except (ValueError, TypeError) as e:
                    validation_errors.append(f"Invalid data types for {symbol}: {e}")
            
            if validation_errors:
                logger.log_error(Exception("Response validation failed"), {
                    "operation": "response_validation",
                    "validation_errors": validation_errors,
                    "response_symbols": list(response_data.keys())
                })
                raise MCPAPIError(f"Response validation failed: {'; '.join(validation_errors)}")
                
        except MCPAPIError:
            raise
        except Exception as e:
            logger.log_error(e, {"operation": "response_validation"})
            raise MCPAPIError(f"Response validation error: {str(e)}")
    
    def parse_response(self, response_data: Dict[str, Any]) -> Dict[str, MarketDataResponse]:
        """
        Parse and validate MCP API response into structured objects.
        
        Args:
            response_data: Raw API response data
            
        Returns:
            Dictionary of MarketDataResponse objects keyed by symbol
            
        Raises:
            MCPAPIError: If parsing fails
        """
        try:
            parsed_data = {}
            
            for symbol, data in response_data.items():
                # Extract required fields with defaults for optional ones
                parsed_data[symbol] = MarketDataResponse(
                    symbol=data["symbol"],
                    price=float(data["price"]),
                    timestamp=int(data["timestamp"]),
                    market_depth=data.get("market_depth", {"bids": [], "asks": []}),
                    volume_24h=float(data.get("volume_24h", 0.0)),
                    price_change_24h=float(data.get("price_change_24h", 0.0))
                )
            
            logger.logger.info(f"Successfully parsed market data for {len(parsed_data)} symbols")
            return parsed_data
            
        except Exception as e:
            logger.log_error(e, {
                "operation": "response_parsing",
                "response_symbols": list(response_data.keys()) if isinstance(response_data, dict) else None
            })
            raise MCPAPIError(f"Response parsing failed: {str(e)}")
    
    def handle_api_errors(self, response: requests.Response) -> None:
        """
        Handle API errors and raise appropriate exceptions.
        
        Args:
            response: The HTTP response object
            
        Raises:
            MCPAPIError: For various API error conditions
        """
        if response.status_code == 200:
            return
        
        # Extract error details for logging
        error_msg = f"MCP API error: {response.status_code}"
        error_details = {
            "status_code": response.status_code,
            "url": response.url,
            "headers": dict(response.headers)
        }
        
        try:
            error_data = response.json()
            if 'error' in error_data:
                error_msg += f" - {error_data['error']}"
                error_details["api_error"] = error_data['error']
        except:
            error_msg += f" - {response.text[:200]}"  # Truncate long responses
            error_details["response_text"] = response.text[:200]
        
        # Log the error with context
        logger.log_error(Exception(error_msg), {
            "operation": "api_error_handling",
            "error_details": error_details
        })
        
        # Raise specific errors based on status code
        if response.status_code == 401:
            raise MCPAPIError("Authentication failed - check API key", response.status_code)
        elif response.status_code == 403:
            raise MCPAPIError("Access forbidden - insufficient permissions", response.status_code)
        elif response.status_code == 404:
            raise MCPAPIError("API endpoint not found", response.status_code)
        elif response.status_code == 429:
            raise MCPAPIError("Rate limit exceeded - too many requests", response.status_code)
        elif response.status_code >= 500:
            raise MCPAPIError("MCP API server error - service unavailable", response.status_code)
        else:
            raise MCPAPIError(f"API request failed with status {response.status_code}", response.status_code)
    
    def get_market_summary(self, symbols: Optional[List[str]] = None) -> Dict[str, MarketDataResponse]:
        """
        Convenience method to fetch and parse market data in one call.
        
        Args:
            symbols: List of symbols to fetch data for
            
        Returns:
            Dictionary of parsed MarketDataResponse objects
        """
        raw_data = self.fetch_market_data(symbols)
        return self.parse_response(raw_data)