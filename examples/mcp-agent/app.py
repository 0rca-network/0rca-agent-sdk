"""
Main FastAPI application for MCP Market Data Agent.
Handles HTTP endpoints, payment verification, and request routing.
"""

import sys
import os
import logging
import time
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Add parent directories to path for SDK imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orca_agent_sdk import AgentConfig, AgentServer
from orca_agent_sdk.core.payment import PaymentManager
from orca_agent_sdk.core.a2a import A2AProtocol, AgentRegistry

from config import get_config
from market_data import MarketDataService, MCPAPIError
from crewai_backend import MCPCrewAIBackend
from a2a_handlers import A2AHandlers
from logging_config import get_logger

# Configure enhanced logging
config = get_config()
logger = get_logger(__name__, config.server.log_level, "logs/mcp_agent.log")

# Initialize FastAPI app
app = FastAPI(
    title="MCP Market Data Agent",
    description="AI-powered market data service with x402 payment integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
agent_config = None
payment_manager = None
market_data_service = None
crewai_backend = None
a2a_handlers = None

def initialize_services():
    """Initialize all agent services and dependencies"""
    global agent_config, payment_manager, market_data_service, crewai_backend, a2a_handlers
    
    try:
        # Get configuration
        config = get_config()
        
        # Log system startup with configuration details
        config_details = {
            "agent_id": config.a2a.agent_id,
            "host": config.server.host,
            "port": config.server.port,
            "debug": config.server.debug,
            "chain_caip": config.payment.chain_caip,
            "token_address": config.payment.token_address,
            "price": config.payment.price,
            "api_endpoint": config.mcp.api_endpoint,
            "timeout_seconds": config.mcp.timeout_seconds,
            "retry_attempts": config.mcp.retry_attempts
        }
        logger.log_system_startup(config_details)
        
        # Create AgentConfig from our configuration
        config_dict = config.to_agent_config_dict()
        agent_config = AgentConfig(**config_dict)
        logger.log_service_initialization("AgentConfig", True, {"agent_id": agent_config.agent_id})
        
        # Initialize payment manager
        try:
            payment_manager = PaymentManager(agent_config)
            logger.log_service_initialization("PaymentManager", True)
        except Exception as e:
            logger.log_service_initialization("PaymentManager", False, error=e)
            raise
        
        # Initialize market data service
        try:
            market_data_service = MarketDataService(config.mcp)
            logger.log_service_initialization("MarketDataService", True, {
                "endpoint": config.mcp.api_endpoint,
                "timeout": config.mcp.timeout_seconds
            })
        except Exception as e:
            logger.log_service_initialization("MarketDataService", False, error=e)
            raise
        
        # Initialize CrewAI backend
        try:
            crewai_backend = MCPCrewAIBackend(config.crewai)
            logger.log_service_initialization("MCPCrewAIBackend", True, {
                "model": config.crewai.model,
                "temperature": config.crewai.temperature
            })
        except Exception as e:
            logger.log_service_initialization("MCPCrewAIBackend", False, error=e)
            raise
        
        # Initialize A2A handlers
        try:
            registry = AgentRegistry()
            a2a_protocol = A2AProtocol(config.a2a.agent_id, registry)
            a2a_handlers = A2AHandlers(a2a_protocol, config.a2a)
            logger.log_service_initialization("A2AHandlers", True, {
                "agent_id": config.a2a.agent_id
            })
        except Exception as e:
            logger.log_service_initialization("A2AHandlers", False, error=e)
            raise
        
        logger.logger.info("All services initialized successfully")
        
    except Exception as e:
        logger.log_error(e, {"phase": "service_initialization"}, "CRITICAL")
        raise

@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    initialize_services()
    config = get_config()
    logger.logger.info(f"MCP Market Data Agent started on {config.server.host}:{config.server.port}")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up services on application shutdown"""
    try:
        shutdown_details = {
            "services_shutdown": [],
            "errors": []
        }
        
        # Close any open connections or resources
        if payment_manager:
            try:
                # PaymentManager cleanup if needed
                shutdown_details["services_shutdown"].append("PaymentManager")
            except Exception as e:
                shutdown_details["errors"].append(f"PaymentManager: {str(e)}")
        
        if market_data_service:
            try:
                # MarketDataService cleanup if needed
                shutdown_details["services_shutdown"].append("MarketDataService")
            except Exception as e:
                shutdown_details["errors"].append(f"MarketDataService: {str(e)}")
        
        if crewai_backend:
            try:
                # CrewAI backend cleanup if needed
                shutdown_details["services_shutdown"].append("MCPCrewAIBackend")
            except Exception as e:
                shutdown_details["errors"].append(f"MCPCrewAIBackend: {str(e)}")
        
        if a2a_handlers:
            try:
                # A2A handlers cleanup if needed
                shutdown_details["services_shutdown"].append("A2AHandlers")
            except Exception as e:
                shutdown_details["errors"].append(f"A2AHandlers: {str(e)}")
        
        logger.log_system_shutdown(shutdown_details)
        
    except Exception as e:
        logger.log_error(e, {"phase": "system_shutdown"}, "ERROR")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    config = get_config()
    
    # Check service health
    services_status = {
        "payment_manager": payment_manager is not None,
        "market_data_service": market_data_service is not None,
        "crewai_backend": crewai_backend is not None,
        "a2a_handlers": a2a_handlers is not None
    }
    
    # Test MCP API connectivity
    mcp_healthy = False
    if market_data_service:
        try:
            # Quick health check - this should be a lightweight operation
            mcp_healthy = True  # For now, assume healthy if service exists
        except Exception as e:
            logger.warning(f"MCP API health check failed: {e}")
            mcp_healthy = False
    
    all_healthy = all(services_status.values()) and mcp_healthy
    
    response_data = {
        "status": "healthy" if all_healthy else "degraded",
        "agent_id": config.a2a.agent_id,
        "version": "1.0.0",
        "services": services_status,
        "external_services": {
            "mcp_api": mcp_healthy
        },
        "timestamp": int(time.time() * 1000)
    }
    
    status_code = 200 if all_healthy else 503
    return JSONResponse(status_code=status_code, content=response_data)

def verify_payment(request: Request) -> bool:
    """Dependency to verify x402 payment"""
    start_time = time.time()
    
    try:
        # Check for x402 payment token in Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        payment_details = {
            "token_present": bool(auth_header.startswith("x402 ")),
            "method": "local_signature"
        }
        
        if not auth_header.startswith("x402 "):
            logger.log_payment_verification(False, payment_details, {
                "reason": "missing_authorization_header",
                "header_present": bool(auth_header),
                "header_format": "invalid" if auth_header else "missing"
            })
            return False
        
        # Extract payment token
        payment_token = auth_header[5:]  # Remove "x402 " prefix
        
        if not payment_token:
            logger.log_payment_verification(False, payment_details, {
                "reason": "empty_payment_token",
                "token_length": 0
            })
            return False
        
        # Decode and verify payment using PaymentManager
        try:
            payment_obj = payment_manager.decode_payment(payment_token)
            
            # Verify signature locally first
            if not payment_manager.verify_signature(payment_obj):
                verification_time = int((time.time() - start_time) * 1000)
                logger.log_payment_verification(False, payment_details, {
                    "reason": "signature_verification_failed",
                    "verification_time_ms": verification_time
                })
                return False
            
            # For now, we'll use local signature verification
            # In production, this would integrate with Cronos facilitator
            verification_time = int((time.time() - start_time) * 1000)
            payment_details["verification_time_ms"] = verification_time
            logger.log_payment_verification(True, payment_details)
            return True
            
        except Exception as decode_error:
            verification_time = int((time.time() - start_time) * 1000)
            logger.log_payment_verification(False, payment_details, {
                "reason": "token_decode_error",
                "error_message": str(decode_error),
                "verification_time_ms": verification_time
            })
            return False
            
    except Exception as e:
        verification_time = int((time.time() - start_time) * 1000)
        logger.log_payment_verification(False, {"token_present": False, "method": "error"}, {
            "reason": "verification_exception",
            "error_message": str(e),
            "verification_time_ms": verification_time
        })
        logger.log_error(e, {"operation": "payment_verification"})
        return False

@app.post("/chat")
async def chat_endpoint(
    request: Request,
    query: Dict[str, Any],
    payment_verified: bool = Depends(verify_payment)
):
    """
    Main chat endpoint for market data queries.
    Requires x402 payment verification.
    """
    start_time = time.time()
    
    try:
        if not payment_verified:
            # Build payment requirements using PaymentManager
            requirements = payment_manager.build_requirements()
            challenge = payment_manager.encode_challenge(requirements)
            
            logger.logger.info("Payment required - returning x402 challenge")
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment required",
                    "message": "This endpoint requires payment to access market data",
                    "accepts": requirements
                },
                headers={"WWW-Authenticate": f"x402 {challenge}"}
            )
        
        # Extract query from request
        user_query = query.get("message", "")
        if not user_query:
            raise HTTPException(status_code=400, detail="Message is required")
        
        logger.logger.info(f"Processing paid query: {user_query}")
        
        # Extract symbols from query if specified (simple implementation)
        symbols = query.get("symbols", None)
        
        try:
            # Fetch market data using the service
            market_data = market_data_service.get_market_summary(symbols)
            
            # Process market data through CrewAI backend for natural language response
            try:
                ai_response = crewai_backend.process_market_data(market_data, user_query)
                processing_time = int((time.time() - start_time) * 1000)
                
                logger.log_processing_performance("chat_request", processing_time, {
                    "symbols_count": len(symbols) if symbols else 0,
                    "market_data_count": len(market_data),
                    "ai_processing": True
                })
                
                return {
                    "result": ai_response,
                    "market_data": {
                        symbol: {
                            "symbol": data.symbol,
                            "price": data.price,
                            "timestamp": data.timestamp,
                            "volume_24h": data.volume_24h,
                            "price_change_24h": data.price_change_24h
                        } for symbol, data in market_data.items()
                    },
                    "timestamp": int(time.time() * 1000),
                    "processing_time_ms": processing_time
                }
                
            except Exception as ai_error:
                logger.log_error(ai_error, {
                    "operation": "crewai_processing",
                    "user_query": user_query,
                    "symbols": symbols,
                    "market_data_available": bool(market_data)
                })
                
                # Fallback to raw market data if AI processing fails
                processing_time = int((time.time() - start_time) * 1000)
                
                return {
                    "result": crewai_backend.handle_processing_errors(ai_error, market_data),
                    "market_data": {
                        symbol: {
                            "symbol": data.symbol,
                            "price": data.price,
                            "timestamp": data.timestamp,
                            "volume_24h": data.volume_24h,
                            "price_change_24h": data.price_change_24h
                        } for symbol, data in market_data.items()
                    },
                    "timestamp": int(time.time() * 1000),
                    "processing_time_ms": processing_time,
                    "ai_processing_error": True
                }
            
        except MCPAPIError as e:
            logger.log_error(e, {
                "operation": "market_data_fetch",
                "user_query": user_query,
                "symbols": symbols,
                "api_status_code": e.status_code
            })
            
            if e.status_code and e.status_code >= 500:
                raise HTTPException(status_code=503, detail=f"Market data service unavailable: {e.message}")
            else:
                raise HTTPException(status_code=502, detail=f"Market data error: {e.message}")
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.log_error(e, {
            "operation": "chat_endpoint",
            "user_query": query.get("message", ""),
            "symbols": query.get("symbols")
        })
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/a2a/send")
async def a2a_send_endpoint(message: Dict[str, Any]):
    """Send A2A message to another agent"""
    try:
        # Extract required fields from request
        to_agent_id = message.get("to_agent_id")
        action = message.get("action")
        payload = message.get("payload", {})
        
        if not to_agent_id or not action:
            error_details = {
                "type": "validation_error",
                "message": "Missing required fields: to_agent_id and action are required",
                "validation_errors": ["to_agent_id required", "action required"]
            }
            
            logger.log_a2a_communication(False, {
                "direction": "send",
                "action": action,
                "to_agent": to_agent_id
            }, error_details)
            
            raise HTTPException(
                status_code=400, 
                detail="Missing required fields: to_agent_id and action are required"
            )
        
        # Send message using A2A handlers
        result = a2a_handlers.send_message(to_agent_id, action, payload)
        
        logger.log_a2a_communication(True, {
            "direction": "send",
            "action": action,
            "to_agent": to_agent_id,
            "message_id": result.get("message_id")
        })
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.log_a2a_communication(False, {
            "direction": "send",
            "action": message.get("action"),
            "to_agent": message.get("to_agent_id")
        }, {
            "type": "unexpected_error",
            "message": str(e)
        })
        logger.log_error(e, {"operation": "a2a_send", "message": message})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/a2a/receive")
async def a2a_receive_endpoint(message: Dict[str, Any]):
    """Receive A2A message from another agent"""
    try:
        # Process message using A2A handlers
        result = a2a_handlers.receive_message(message)
        
        logger.log_a2a_communication(True, {
            "direction": "receive",
            "action": message.get("task", {}).get("action"),
            "from_agent": message.get("header", {}).get("from"),
            "message_id": message.get("header", {}).get("message_id")
        })
        
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.log_a2a_communication(False, {
            "direction": "receive",
            "action": message.get("task", {}).get("action"),
            "from_agent": message.get("header", {}).get("from"),
            "message_id": message.get("header", {}).get("message_id")
        }, {
            "type": "processing_error",
            "message": str(e)
        })
        logger.log_error(e, {"operation": "a2a_receive", "message": message})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/a2a/agents")
async def list_agents_endpoint():
    """List registered agents in the registry"""
    try:
        result = a2a_handlers.get_registered_agents()
        logger.logger.info(f"Listed {result.get('count', 0)} registered agents")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.log_error(e, {"operation": "list_agents"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payment/info")
async def payment_info_endpoint():
    """Get payment information and requirements"""
    try:
        config = get_config()
        requirements = payment_manager.build_requirements()
        
        logger.logger.info("Payment info requested")
        
        return {
            "payment_required": True,
            "requirements": requirements,
            "agent_id": config.a2a.agent_id,
            "price": config.payment.price,
            "token": config.payment.token_address,
            "chain": config.payment.chain_caip,
            "resource": "/agent"
        }
        
    except Exception as e:
        logger.log_error(e, {"operation": "payment_info"})
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/payment/status")
async def payment_status_endpoint(request: Request):
    """Check payment status for the current request"""
    try:
        # Check if payment is provided and valid
        payment_verified = verify_payment(request)
        
        if payment_verified:
            logger.logger.info("Payment status check: verified")
            return {
                "status": "verified",
                "message": "Payment verification successful",
                "access_granted": True
            }
        else:
            # Return payment requirements
            requirements = payment_manager.build_requirements()
            challenge = payment_manager.encode_challenge(requirements)
            
            logger.logger.info("Payment status check: required")
            return JSONResponse(
                status_code=402,
                content={
                    "status": "required",
                    "message": "Payment required for access",
                    "accepts": requirements
                },
                headers={"WWW-Authenticate": f"x402 {challenge}"}
            )
            
    except Exception as e:
        logger.log_error(e, {"operation": "payment_status"})
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/a2a/register")
async def register_agent_endpoint(agent_info: Dict[str, Any]):
    """Register another agent in the local registry"""
    try:
        agent_id = agent_info.get("agent_id")
        endpoint = agent_info.get("endpoint")
        capabilities = agent_info.get("capabilities", [])
        name = agent_info.get("name", "")
        
        if not agent_id or not endpoint:
            logger.logger.warning(f"Agent registration failed: missing required fields")
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: agent_id and endpoint are required"
            )
        
        result = a2a_handlers.register_agent(agent_id, endpoint, capabilities, name)
        logger.logger.info(f"Agent registered successfully: {agent_id}")
        return result
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.log_error(e, {"operation": "agent_registration", "agent_info": agent_info})
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    import time
    
    config = get_config()
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level=config.server.log_level.lower()
    )