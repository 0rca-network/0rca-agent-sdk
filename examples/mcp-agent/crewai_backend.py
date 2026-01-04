"""
CrewAI Backend Adapter for MCP Market Data Agent.
Extends the existing CrewAI backend for market data processing.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("google-generativeai not available, using fallback implementation")

try:
    from .config import CrewAIConfig
    from .market_data import MarketDataResponse
    from .logging_config import get_logger
except ImportError:
    from config import CrewAIConfig
    from market_data import MarketDataResponse
    from logging_config import get_logger

logger = get_logger(__name__)

class MCPCrewAIBackend:
    """
    Extended CrewAI backend for market data processing.
    Integrates with Google's Gemini API for natural language generation.
    """
    
    def __init__(self, crewai_config: CrewAIConfig):
        self.config = crewai_config
        self.model = None
        
        # Initialize the AI model if available
        if GENAI_AVAILABLE and self.config.api_key:
            try:
                genai.configure(api_key=self.config.api_key)
                
                # Configure the model with safety settings
                generation_config = {
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                }
                
                safety_settings = {
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                }
                
                self.model = genai.GenerativeModel(
                    model_name=self.config.model,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
                
                logger.log_service_initialization("MCPCrewAIBackend", True, {
                    "model": self.config.model,
                    "temperature": self.config.temperature,
                    "max_tokens": self.config.max_tokens
                })
                
            except Exception as e:
                logger.log_service_initialization("MCPCrewAIBackend", False, error=e)
                self.model = None
        else:
            logger.logger.warning("CrewAI backend initialized without AI model (missing dependencies or API key)")
            logger.log_service_initialization("MCPCrewAIBackend", False, {
                "reason": "missing_dependencies_or_api_key",
                "genai_available": GENAI_AVAILABLE,
                "api_key_present": bool(self.config.api_key)
            })
    
    def process_market_data(self, market_data: Dict[str, MarketDataResponse], user_query: str = "") -> str:
        """
        Process market data into natural language response.
        
        Args:
            market_data: Dictionary of market data responses keyed by symbol
            user_query: Original user query for context
            
        Returns:
            Natural language explanation of the market data
        """
        start_time = time.time()
        
        try:
            logger.logger.info(f"Processing market data for {len(market_data)} symbols")
            
            if not market_data:
                return "No market data available at this time."
            
            # If AI model is not available, use fallback
            if not self.model:
                logger.logger.warning("AI model not available, using fallback response")
                return self._generate_fallback_response(market_data, user_query)
            
            # Prepare market data for AI processing
            market_summary = self._prepare_market_data_for_ai(market_data)
            
            # Create prompt for natural language generation
            prompt = self._create_market_analysis_prompt(market_summary, user_query)
            
            # Generate AI response with timeout
            try:
                response = self.model.generate_content(prompt)
                processing_time = int((time.time() - start_time) * 1000)
                
                if processing_time > self.config.processing_timeout * 1000:
                    logger.logger.warning(f"AI processing took {processing_time}ms (timeout: {self.config.processing_timeout * 1000}ms)")
                
                if response.text:
                    logger.log_processing_performance("ai_market_analysis", processing_time, {
                        "symbols_count": len(market_data),
                        "query_length": len(user_query),
                        "response_length": len(response.text)
                    })
                    return response.text.strip()
                else:
                    logger.logger.warning("AI model returned empty response")
                    return self._generate_fallback_response(market_data, user_query)
                    
            except Exception as e:
                processing_time = int((time.time() - start_time) * 1000)
                logger.log_error(e, {
                    "operation": "ai_generation",
                    "processing_time_ms": processing_time,
                    "symbols_count": len(market_data),
                    "query": user_query
                })
                return self.handle_processing_errors(e, market_data)
                
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.log_error(e, {
                "operation": "process_market_data",
                "processing_time_ms": processing_time,
                "symbols_count": len(market_data) if market_data else 0
            })
            return self.handle_processing_errors(e, market_data)
    
    def _prepare_market_data_for_ai(self, market_data: Dict[str, MarketDataResponse]) -> Dict[str, Any]:
        """
        Prepare market data in a structured format for AI processing.
        
        Args:
            market_data: Raw market data responses
            
        Returns:
            Structured data suitable for AI analysis
        """
        prepared_data = {}
        
        for symbol, data in market_data.items():
            prepared_data[symbol] = {
                "symbol": data.symbol,
                "current_price": data.price,
                "price_change_24h": data.price_change_24h,
                "price_change_percent": f"{data.price_change_24h:+.2f}%",
                "volume_24h": data.volume_24h,
                "timestamp": datetime.fromtimestamp(data.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S UTC"),
                "market_depth_summary": {
                    "bid_count": len(data.market_depth.get("bids", [])),
                    "ask_count": len(data.market_depth.get("asks", [])),
                    "has_depth_data": bool(data.market_depth.get("bids") or data.market_depth.get("asks"))
                }
            }
        
        return prepared_data
    
    def _create_market_analysis_prompt(self, market_data: Dict[str, Any], user_query: str) -> str:
        """
        Create a comprehensive prompt for AI market analysis.
        
        Args:
            market_data: Prepared market data
            user_query: Original user query
            
        Returns:
            Formatted prompt for AI generation
        """
        symbols = list(market_data.keys())
        
        prompt = f"""You are a professional cryptocurrency market analyst. Analyze the following market data and provide a clear, informative response.

User Query: "{user_query}"

Market Data:
{json.dumps(market_data, indent=2)}

Please provide a comprehensive analysis that includes:

1. **Current Market Status**: Summarize the current prices and recent performance
2. **Price Movements**: Highlight significant price changes and trends
3. **Market Activity**: Comment on trading volumes and market depth where available
4. **Key Insights**: Provide relevant observations about the market conditions

Guidelines:
- Use clear, professional language suitable for both beginners and experienced traders
- Include specific numbers and percentages where relevant
- Organize information clearly when multiple assets are involved
- Focus on factual analysis based on the provided data
- Keep the response concise but informative (aim for 200-400 words)
- If analyzing multiple symbols, organize by asset for clarity

Response:"""
        
        return prompt
    
    def _generate_fallback_response(self, market_data: Dict[str, MarketDataResponse], user_query: str = "") -> str:
        """
        Generate a structured response without AI when the model is unavailable.
        
        Args:
            market_data: Market data to format
            user_query: Original user query
            
        Returns:
            Formatted market data response
        """
        symbols = list(market_data.keys())
        
        if len(symbols) == 1:
            # Single asset response
            symbol = symbols[0]
            data = market_data[symbol]
            
            change_direction = "up" if data.price_change_24h >= 0 else "down"
            change_color = "📈" if data.price_change_24h >= 0 else "📉"
            
            response = f"""Market Data for {symbol} {change_color}

Current Price: ${data.price:,.2f}
24h Change: {data.price_change_24h:+.2f}% ({change_direction})
24h Volume: ${data.volume_24h:,.2f}
Last Updated: {datetime.fromtimestamp(data.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")}

The {symbol} is currently trading at ${data.price:,.2f}, showing a {abs(data.price_change_24h):.2f}% movement {change_direction} over the past 24 hours."""
            
        else:
            # Multi-asset response
            response = f"Market Data Summary for {len(symbols)} Assets:\n\n"
            
            for symbol, data in market_data.items():
                change_emoji = "📈" if data.price_change_24h >= 0 else "📉"
                response += f"{change_emoji} {symbol}: ${data.price:,.2f} ({data.price_change_24h:+.2f}%)\n"
            
            response += f"\nData as of {datetime.fromtimestamp(list(market_data.values())[0].timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        return response
    
    def generate_summary(self, raw_data: Dict[str, Any], context: str = "") -> str:
        """
        Generate comprehensive market analysis from raw data.
        
        Args:
            raw_data: Raw market data from API
            context: Additional context for the summary
            
        Returns:
            Natural language market summary
        """
        try:
            logger.info("Generating market summary")
            
            if not raw_data:
                return "No market data available for summary generation."
            
            # If AI model is not available, use structured fallback
            if not self.model:
                return self._generate_structured_summary(raw_data, context)
            
            # Create summary prompt
            prompt = f"""Analyze the following cryptocurrency market data and provide a comprehensive market summary.

Context: {context}

Raw Market Data:
{json.dumps(raw_data, indent=2)}

Please provide a market summary that includes:
1. Overall market sentiment and trends
2. Notable price movements and patterns
3. Trading activity analysis
4. Key market insights and observations

Keep the summary informative yet accessible, suitable for both novice and experienced traders."""
            
            try:
                response = self.model.generate_content(prompt)
                if response.text:
                    return response.text.strip()
                else:
                    return self._generate_structured_summary(raw_data, context)
                    
            except Exception as e:
                logger.error(f"AI summary generation failed: {e}")
                return self._generate_structured_summary(raw_data, context)
                
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return f"Summary generation temporarily unavailable. Error: {str(e)}"
    
    def _generate_structured_summary(self, raw_data: Dict[str, Any], context: str = "") -> str:
        """
        Generate a structured summary without AI.
        
        Args:
            raw_data: Raw market data
            context: Additional context
            
        Returns:
            Structured market summary
        """
        symbols = list(raw_data.keys())
        
        summary = f"Market Summary ({len(symbols)} assets analyzed)\n\n"
        
        if context:
            summary += f"Context: {context}\n\n"
        
        # Analyze price movements
        positive_movers = []
        negative_movers = []
        
        for symbol, data in raw_data.items():
            change = data.get("price_change_24h", 0)
            if change > 0:
                positive_movers.append((symbol, change))
            elif change < 0:
                negative_movers.append((symbol, change))
        
        if positive_movers:
            positive_movers.sort(key=lambda x: x[1], reverse=True)
            summary += f"📈 Top Gainers: {', '.join([f'{s} (+{c:.2f}%)' for s, c in positive_movers[:3]])}\n"
        
        if negative_movers:
            negative_movers.sort(key=lambda x: x[1])
            summary += f"📉 Top Decliners: {', '.join([f'{s} ({c:.2f}%)' for s, c in negative_movers[:3]])}\n"
        
        summary += f"\nData timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        return summary
    
    def handle_processing_errors(self, error: Exception, market_data: Optional[Dict[str, MarketDataResponse]] = None) -> str:
        """
        Handle AI processing failures gracefully.
        
        Args:
            error: The exception that occurred
            market_data: Optional market data to include in fallback response
            
        Returns:
            Error message with fallback data if available
        """
        logger.log_error(error, {
            "operation": "ai_processing_error_handling",
            "market_data_available": bool(market_data),
            "symbols_count": len(market_data) if market_data else 0
        })
        
        error_msg = "AI processing temporarily unavailable. "
        
        if market_data:
            error_msg += "Here's the raw market data:\n\n"
            error_msg += self._generate_fallback_response(market_data)
        else:
            error_msg += f"Error details: {str(error)}"
        
        return error_msg