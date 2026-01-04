"""
A2A (Agent-to-Agent) Communication Handlers.
Manages message sending, receiving, and validation for inter-agent communication.
"""

import logging
import time
from typing import Dict, Any, Optional
from fastapi import HTTPException
from orca_agent_sdk.core.a2a import A2AProtocol, AgentRegistry
from config import A2AConfig
from logging_config import get_logger

logger = get_logger(__name__)

class A2AHandlers:
    """
    Handlers for Agent-to-Agent communication.
    Implements message sending, receiving, and validation with comprehensive error handling.
    """
    
    def __init__(self, a2a_protocol: A2AProtocol, a2a_config: A2AConfig):
        self.protocol = a2a_protocol
        self.config = a2a_config
        self.registry = a2a_protocol.registry
        logger.log_service_initialization("A2AHandlers", True, {
            "agent_id": self.config.agent_id
        })
    
    def send_message(self, to_agent_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send message to another agent via A2A protocol.
        
        Args:
            to_agent_id: Target agent identifier
            action: Action to perform (e.g., "query_market_data", "notify")
            payload: Message payload data
            
        Returns:
            Dict containing response from target agent
            
        Raises:
            HTTPException: If agent not found or communication fails
        """
        try:
            logger.logger.info(f"Sending A2A message to {to_agent_id}: action={action}")
            
            # Validate target agent exists in registry
            target_agent = self.registry.get_agent(to_agent_id)
            if not target_agent:
                error_details = {
                    "type": "agent_not_found",
                    "message": f"Agent {to_agent_id} not found in registry"
                }
                
                logger.log_a2a_communication(False, {
                    "direction": "send",
                    "action": action,
                    "to_agent": to_agent_id
                }, error_details)
                
                raise HTTPException(
                    status_code=404, 
                    detail=f"Agent {to_agent_id} not found in registry"
                )
            
            # Create and send message using protocol
            start_time = time.time()
            response = self.protocol.send_message(to_agent_id, action, payload)
            
            # Log successful communication
            duration = time.time() - start_time
            logger.log_a2a_communication(True, {
                "direction": "send",
                "action": action,
                "to_agent": to_agent_id,
                "message_id": response.get("message_id")
            })
            
            logger.log_processing_performance("a2a_send", int(duration * 1000), {
                "target_agent": to_agent_id,
                "action": action,
                "payload_size": len(str(payload))
            })
            
            return {
                "status": "success",
                "target_agent": to_agent_id,
                "action": action,
                "response": response,
                "duration_ms": int(duration * 1000)
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            error_details = {
                "type": "validation_error",
                "message": str(e)
            }
            logger.log_a2a_communication(False, {
                "direction": "send",
                "action": action,
                "to_agent": to_agent_id
            }, error_details)
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            error_details = {
                "type": "communication_error",
                "message": str(e)
            }
            logger.log_a2a_communication(False, {
                "direction": "send",
                "action": action,
                "to_agent": to_agent_id
            }, error_details)
            raise HTTPException(status_code=503, detail=f"Network communication failure: {str(e)}")
        except Exception as e:
            error_details = {
                "type": "unexpected_error",
                "message": str(e)
            }
            logger.log_a2a_communication(False, {
                "direction": "send",
                "action": action,
                "to_agent": to_agent_id
            }, error_details)
            logger.log_error(e, {"operation": "a2a_send", "target_agent": to_agent_id, "action": action})
            raise HTTPException(status_code=500, detail=f"Internal A2A error: {str(e)}")
    
    def receive_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming A2A message from another agent.
        
        Args:
            message: A2A message following the protocol schema
            
        Returns:
            Dict containing processing result
            
        Raises:
            HTTPException: If message validation fails or processing errors occur
        """
        try:
            # Validate message schema first
            if not self.validate_message_schema(message):
                error_details = {
                    "type": "schema_validation_error",
                    "message": "Invalid A2A message schema"
                }
                
                logger.log_a2a_communication(False, {
                    "direction": "receive",
                    "action": message.get("task", {}).get("action"),
                    "from_agent": message.get("header", {}).get("from"),
                    "message_id": message.get("header", {}).get("message_id")
                }, error_details)
                
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid A2A message schema"
                )
            
            # Extract message components
            header = message["header"]
            task = message["task"]
            from_agent = header["from"]
            action = task["action"]
            payload = task["payload"]
            
            logger.logger.info(f"Processing A2A message from {from_agent}: action={action}")
            
            # Validate message using protocol
            validated_message = self.protocol.receive_message(message)
            
            # Process the message based on action
            result = self._process_message_action(action, payload, from_agent)
            
            logger.log_a2a_communication(True, {
                "direction": "receive",
                "action": action,
                "from_agent": from_agent,
                "message_id": header["message_id"]
            })
            
            return {
                "status": "success",
                "message_id": header["message_id"],
                "from_agent": from_agent,
                "action": action,
                "result": result,
                "timestamp": int(time.time() * 1000)
            }
            
        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except ValueError as e:
            error_details = {
                "type": "validation_error",
                "message": str(e)
            }
            logger.log_a2a_communication(False, {
                "direction": "receive",
                "action": message.get("task", {}).get("action"),
                "from_agent": message.get("header", {}).get("from"),
                "message_id": message.get("header", {}).get("message_id")
            }, error_details)
            raise HTTPException(status_code=400, detail=f"Message validation failed: {str(e)}")
        except Exception as e:
            error_details = {
                "type": "processing_error",
                "message": str(e)
            }
            logger.log_a2a_communication(False, {
                "direction": "receive",
                "action": message.get("task", {}).get("action"),
                "from_agent": message.get("header", {}).get("from"),
                "message_id": message.get("header", {}).get("message_id")
            }, error_details)
            logger.log_error(e, {"operation": "a2a_receive", "message": message})
            raise HTTPException(status_code=500, detail=f"Message processing failed: {str(e)}")
    
    def validate_message_schema(self, message: Dict[str, Any]) -> bool:
        """
        Validate A2A message schema according to protocol specification.
        
        Args:
            message: Message to validate
            
        Returns:
            True if message is valid, False otherwise
        """
        validation_errors = []
        
        try:
            # Check top-level structure
            if not isinstance(message, dict):
                validation_errors.append("Message is not a dictionary")
                return False
            
            # Required top-level fields
            required_fields = ['header', 'task']
            for field in required_fields:
                if field not in message:
                    validation_errors.append(f"Missing required field: {field}")
            
            # Validate header structure
            header = message.get('header', {})
            if not isinstance(header, dict):
                validation_errors.append("Header is not a dictionary")
            else:
                header_fields = ['message_id', 'from', 'to', 'timestamp']
                for field in header_fields:
                    if field not in header:
                        validation_errors.append(f"Missing header field: {field}")
                    elif not header[field]:  # Check for empty values
                        validation_errors.append(f"Empty header field: {field}")
            
            # Validate task structure
            task = message.get('task', {})
            if not isinstance(task, dict):
                validation_errors.append("Task is not a dictionary")
            else:
                task_fields = ['action', 'payload']
                for field in task_fields:
                    if field not in task:
                        validation_errors.append(f"Missing task field: {field}")
            
            # Validate specific field types
            if header and 'timestamp' in header and not isinstance(header['timestamp'], (int, float)):
                validation_errors.append("Timestamp must be numeric")
            
            if task and 'action' in task and (not isinstance(task['action'], str) or not task['action'].strip()):
                validation_errors.append("Action must be a non-empty string")
            
            if task and 'payload' in task and not isinstance(task['payload'], dict):
                validation_errors.append("Payload must be a dictionary")
            
            # Validate destination matches our agent
            if header and 'to' in header and header['to'] != self.config.agent_id:
                validation_errors.append(f"Message destination {header['to']} does not match agent ID {self.config.agent_id}")
            
            # Log validation errors if any
            if validation_errors:
                logger.log_error(Exception("A2A message validation failed"), {
                    "operation": "message_validation",
                    "validation_errors": validation_errors,
                    "message_id": header.get("message_id") if header else None,
                    "from_agent": header.get("from") if header else None
                })
                return False
            
            return True
            
        except Exception as e:
            logger.log_error(e, {"operation": "message_validation", "message": message})
            return False
    
    def _process_message_action(self, action: str, payload: Dict[str, Any], from_agent: str) -> Dict[str, Any]:
        """
        Process A2A message based on action type.
        
        Args:
            action: Action to perform
            payload: Message payload
            from_agent: Source agent ID
            
        Returns:
            Processing result
        """
        try:
            # Handle different action types
            if action == "ping":
                return self._handle_ping(payload, from_agent)
            elif action == "query_market_data":
                return self._handle_market_data_query(payload, from_agent)
            elif action == "notify":
                return self._handle_notification(payload, from_agent)
            elif action == "status":
                return self._handle_status_request(payload, from_agent)
            else:
                logger.warning(f"Unknown action type: {action}")
                return {
                    "status": "unknown_action",
                    "message": f"Action '{action}' is not supported",
                    "supported_actions": ["ping", "query_market_data", "notify", "status"]
                }
                
        except Exception as e:
            logger.error(f"Action processing error for {action}: {e}")
            return {
                "status": "error",
                "message": f"Failed to process action '{action}': {str(e)}"
            }
    
    def _handle_ping(self, payload: Dict[str, Any], from_agent: str) -> Dict[str, Any]:
        """Handle ping action for connectivity testing"""
        logger.logger.info(f"Ping received from {from_agent}")
        return {
            "status": "pong",
            "agent_id": self.config.agent_id,
            "timestamp": int(time.time() * 1000),
            "message": payload.get("message", "")
        }
    
    def _handle_market_data_query(self, payload: Dict[str, Any], from_agent: str) -> Dict[str, Any]:
        """Handle market data query from another agent"""
        logger.logger.info(f"Market data query from {from_agent}: {payload}")
        
        # This would integrate with our market data service
        # For now, return a basic response indicating the capability
        return {
            "status": "market_data_available",
            "message": "Market data queries require payment verification",
            "endpoint": "/chat",
            "payment_required": True,
            "supported_symbols": ["BTC", "ETH", "CRO"]
        }
    
    def _handle_notification(self, payload: Dict[str, Any], from_agent: str) -> Dict[str, Any]:
        """Handle notification from another agent"""
        notification_type = payload.get("type", "general")
        message = payload.get("message", "")
        
        logger.logger.info(f"Notification from {from_agent} [{notification_type}]: {message}")
        
        return {
            "status": "notification_received",
            "type": notification_type,
            "acknowledged": True
        }
    
    def _handle_status_request(self, payload: Dict[str, Any], from_agent: str) -> Dict[str, Any]:
        """Handle status request from another agent"""
        logger.logger.info(f"Status request from {from_agent}")
        
        return {
            "status": "online",
            "agent_id": self.config.agent_id,
            "capabilities": ["market_data", "payment_verification", "a2a_communication"],
            "uptime": int(time.time() * 1000),  # Simplified uptime
            "version": "1.0.0"
        }
    
    def register_agent(self, agent_id: str, endpoint: str, capabilities: list = None, name: str = "") -> Dict[str, Any]:
        """
        Register another agent in the local registry.
        
        Args:
            agent_id: Agent identifier
            endpoint: Agent's HTTP endpoint
            capabilities: List of agent capabilities
            name: Human-readable agent name
            
        Returns:
            Registration result
        """
        try:
            self.registry.register(
                agent_id=agent_id,
                endpoint=endpoint,
                capabilities=capabilities or [],
                name=name
            )
            
            logger.logger.info(f"Registered agent {agent_id} at {endpoint}")
            
            return {
                "status": "registered",
                "agent_id": agent_id,
                "endpoint": endpoint,
                "capabilities": capabilities or []
            }
            
        except Exception as e:
            logger.log_error(e, {
                "operation": "agent_registration",
                "agent_id": agent_id,
                "endpoint": endpoint
            })
            raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")
    
    def get_registered_agents(self) -> Dict[str, Any]:
        """
        Get list of registered agents.
        
        Returns:
            Dictionary of registered agents
        """
        try:
            # Access local agents from registry
            agents = {}
            if hasattr(self.registry, '_local_agents'):
                for agent_id, agent_info in self.registry._local_agents.items():
                    agents[agent_id] = {
                        "agent_id": agent_info.agent_id,
                        "endpoint": agent_info.endpoint,
                        "capabilities": agent_info.capabilities,
                        "name": agent_info.name
                    }
            
            logger.logger.info(f"Retrieved {len(agents)} registered agents")
            
            return {
                "status": "success",
                "count": len(agents),
                "agents": agents
            }
            
        except Exception as e:
            logger.log_error(e, {"operation": "get_registered_agents"})
            raise HTTPException(status_code=500, detail=f"Registry access failed: {str(e)}")