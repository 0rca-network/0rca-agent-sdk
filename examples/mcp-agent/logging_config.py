"""
Centralized logging configuration for MCP Market Data Agent.
Provides structured logging with appropriate severity levels and context details.
"""

import logging
import logging.handlers
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured log messages with context.
    """
    
    def format(self, record):
        # Create structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra context if present
        if hasattr(record, 'context'):
            log_entry["context"] = record.context
        
        # Add payment context if present
        if hasattr(record, 'payment_context'):
            log_entry["payment_context"] = record.payment_context
        
        # Add API context if present
        if hasattr(record, 'api_context'):
            log_entry["api_context"] = record.api_context
        
        # Add A2A context if present
        if hasattr(record, 'a2a_context'):
            log_entry["a2a_context"] = record.a2a_context
        
        return json.dumps(log_entry)

class MCPLogger:
    """
    Centralized logger for MCP Market Data Agent with context-aware logging.
    """
    
    def __init__(self, name: str, log_level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Console handler with structured formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            try:
                # Ensure log directory exists
                log_dir = os.path.dirname(log_file)
                if log_dir and not os.path.exists(log_dir):
                    os.makedirs(log_dir)
                
                # Rotating file handler to prevent large log files
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file, 
                    maxBytes=10*1024*1024,  # 10MB
                    backupCount=5
                )
                file_handler.setFormatter(StructuredFormatter())
                self.logger.addHandler(file_handler)
                
            except Exception as e:
                self.logger.error(f"Failed to setup file logging: {e}")
    
    def log_system_startup(self, config_details: Dict[str, Any]):
        """Log system startup with configuration details (without sensitive info)"""
        startup_context = {
            "event_type": "system_startup",
            "agent_id": config_details.get("agent_id"),
            "server_config": {
                "host": config_details.get("host"),
                "port": config_details.get("port"),
                "debug": config_details.get("debug", False)
            },
            "payment_config": {
                "chain": config_details.get("chain_caip"),
                "token": config_details.get("token_address"),
                "price": config_details.get("price")
            },
            "api_config": {
                "endpoint": config_details.get("api_endpoint"),
                "timeout": config_details.get("timeout_seconds"),
                "retry_attempts": config_details.get("retry_attempts")
            }
        }
        
        self.logger.info(
            "MCP Market Data Agent startup successful",
            extra={"context": startup_context}
        )
    
    def log_system_shutdown(self, shutdown_details: Dict[str, Any] = None):
        """Log system shutdown with cleanup details"""
        shutdown_context = {
            "event_type": "system_shutdown",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if shutdown_details:
            shutdown_context.update(shutdown_details)
        
        self.logger.info(
            "MCP Market Data Agent shutdown initiated",
            extra={"context": shutdown_context}
        )
    
    def log_payment_verification(self, success: bool, payment_details: Dict[str, Any], error_details: Optional[Dict[str, Any]] = None):
        """Log payment verification attempts with context"""
        payment_context = {
            "event_type": "payment_verification",
            "success": success,
            "payment_token_present": payment_details.get("token_present", False),
            "verification_method": payment_details.get("method", "local_signature"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if error_details:
            payment_context["error_details"] = error_details
        
        if success:
            self.logger.info(
                "Payment verification successful",
                extra={"payment_context": payment_context}
            )
        else:
            self.logger.warning(
                f"Payment verification failed: {error_details.get('reason', 'Unknown error') if error_details else 'No payment provided'}",
                extra={"payment_context": payment_context}
            )
    
    def log_api_request(self, success: bool, request_details: Dict[str, Any], response_details: Optional[Dict[str, Any]] = None, error_details: Optional[Dict[str, Any]] = None):
        """Log API requests with comprehensive context"""
        api_context = {
            "event_type": "api_request",
            "success": success,
            "endpoint": request_details.get("endpoint"),
            "method": request_details.get("method", "GET"),
            "symbols": request_details.get("symbols"),
            "attempt_number": request_details.get("attempt", 1),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if response_details:
            api_context["response"] = {
                "status_code": response_details.get("status_code"),
                "response_time_ms": response_details.get("response_time_ms"),
                "data_count": response_details.get("data_count")
            }
        
        if error_details:
            api_context["error"] = {
                "type": error_details.get("type"),
                "message": error_details.get("message"),
                "status_code": error_details.get("status_code")
            }
        
        if success:
            self.logger.info(
                f"API request successful: {request_details.get('endpoint')}",
                extra={"api_context": api_context}
            )
        else:
            self.logger.error(
                f"API request failed: {error_details.get('message', 'Unknown error') if error_details else 'Request failed'}",
                extra={"api_context": api_context}
            )
    
    def log_a2a_communication(self, success: bool, message_details: Dict[str, Any], error_details: Optional[Dict[str, Any]] = None):
        """Log A2A communication events with message context"""
        a2a_context = {
            "event_type": "a2a_communication",
            "success": success,
            "direction": message_details.get("direction"),  # "send" or "receive"
            "action": message_details.get("action"),
            "from_agent": message_details.get("from_agent"),
            "to_agent": message_details.get("to_agent"),
            "message_id": message_details.get("message_id"),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if error_details:
            a2a_context["error"] = {
                "type": error_details.get("type"),
                "message": error_details.get("message"),
                "validation_errors": error_details.get("validation_errors")
            }
        
        if success:
            self.logger.info(
                f"A2A {message_details.get('direction')} successful: {message_details.get('action')}",
                extra={"a2a_context": a2a_context}
            )
        else:
            self.logger.error(
                f"A2A {message_details.get('direction')} failed: {error_details.get('message', 'Unknown error') if error_details else 'Communication failed'}",
                extra={"a2a_context": a2a_context}
            )
    
    def log_service_initialization(self, service_name: str, success: bool, details: Dict[str, Any] = None, error: Optional[Exception] = None):
        """Log service initialization events"""
        init_context = {
            "event_type": "service_initialization",
            "service": service_name,
            "success": success,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if details:
            init_context["details"] = details
        
        if success:
            self.logger.info(
                f"Service initialized successfully: {service_name}",
                extra={"context": init_context}
            )
        else:
            init_context["error"] = str(error) if error else "Unknown error"
            self.logger.error(
                f"Service initialization failed: {service_name}",
                extra={"context": init_context},
                exc_info=error
            )
    
    def log_processing_performance(self, operation: str, duration_ms: int, details: Dict[str, Any] = None):
        """Log performance metrics for operations"""
        perf_context = {
            "event_type": "performance_metric",
            "operation": operation,
            "duration_ms": duration_ms,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if details:
            perf_context["details"] = details
        
        # Log as warning if operation is slow
        if duration_ms > 5000:  # 5 seconds
            self.logger.warning(
                f"Slow operation detected: {operation} took {duration_ms}ms",
                extra={"context": perf_context}
            )
        else:
            self.logger.info(
                f"Operation completed: {operation} in {duration_ms}ms",
                extra={"context": perf_context}
            )
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None, severity: str = "ERROR"):
        """Log errors with full context and stack trace"""
        error_context = {
            "event_type": "error",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if context:
            error_context["context"] = context
        
        log_method = getattr(self.logger, severity.lower(), self.logger.error)
        log_method(
            f"Error occurred: {type(error).__name__}: {str(error)}",
            extra={"context": error_context},
            exc_info=error
        )

def get_logger(name: str, log_level: str = "INFO", log_file: Optional[str] = None) -> MCPLogger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually module name)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        
    Returns:
        Configured MCPLogger instance
    """
    return MCPLogger(name, log_level, log_file)