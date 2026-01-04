import logging
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

from orca_agent_sdk.backends.crewai_backend import CrewAIBackend
from orca_agent_sdk.config import AgentConfig

try:
    from .market_data import MarketDataResponse
    from .logging_config import get_logger
except ImportError:
    from market_data import MarketDataResponse
    from logging_config import get_logger

logger = get_logger(__name__)

class MCPCrewAIBackend(CrewAIBackend):
    """
    Extended CrewAI backend for market data processing.
    Uses the orca_agent_sdk CrewAIBackend for core logic.
    """
    
    def __init__(self, crewai_config: Any):
        # We'll initialize via the SDK way later, but for now we shim it
        self.crew_config = crewai_config
        # Construct an AgentConfig to initialize the base backend
        self.sdk_config = AgentConfig(
            agent_id="mcp-market-data-agent",
            price="0.1",
            ai_backend="crewai",
            backend_options={
                "model": crewai_config.model,
                "provider_api_key": crewai_config.api_key,
                "temperature": crewai_config.temperature,
                "mcps": getattr(crewai_config, 'mcps', [])
            }
        )
        self.initialize(self.sdk_config)
        
        logger.log_service_initialization("MCPCrewAIBackend", True, {
            "model": self.crew_config.model,
            "mcps_count": len(getattr(crewai_config, 'mcps', []))
        })
    
    def process_market_data(self, market_data: Dict[str, MarketDataResponse], user_query: str = "") -> str:
        """
        Process market data into natural language response using CrewAI.
        """
        start_time = time.time()
        
        try:
            # Prepare market data for context (if available)
            market_summary = self._prepare_market_data_for_ai(market_data) if market_data else {}
            
            # Construct a comprehensive prompt
            if market_summary:
                prompt = f"""
                User Query: {user_query}
                
                Current Market Data:
                {json.dumps(market_summary, indent=2)}
                
                Please analyze this data and provide a professional response.
                """
            else:
                prompt = user_query
            
            # Use the base handle_prompt which triggers the Crew kickoff
            response = self.handle_prompt(prompt)
            
            processing_time = int((time.time() - start_time) * 1000)
            logger.log_processing_performance("crewai_market_analysis", processing_time, {
                "symbols_count": len(market_data),
                "response_length": len(response)
            })
            
            return response
                
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            logger.log_error(e, {
                "operation": "process_market_data",
                "processing_time_ms": processing_time
            })
            return f"Error processing market data: {str(e)}"
    
    def _prepare_market_data_for_ai(self, market_data: Dict[str, MarketDataResponse]) -> Dict[str, Any]:
        prepared_data = {}
        for symbol, data in market_data.items():
            prepared_data[symbol] = {
                "symbol": data.symbol,
                "current_price": data.price,
                "price_change_24h": f"{data.price_change_24h:+.2f}%",
                "volume_24h": data.volume_24h,
                "timestamp": datetime.fromtimestamp(data.timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S UTC")
            }
        return prepared_data

    def handle_processing_errors(self, error: Exception, market_data: Optional[Dict[str, MarketDataResponse]] = None) -> str:
        return f"AI processing failed: {str(error)}"
