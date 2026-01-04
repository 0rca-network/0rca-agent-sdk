# MCP Market Data Agent

A comprehensive example of 0rca-agent-sdk integration that provides AI-powered cryptocurrency market data services through HTTP endpoints and Agent-to-Agent (A2A) communication.

## Features

- **x402 Payment Integration**: Secure payment verification using Cronos facilitator
- **MCP API Integration**: Real-time market data from Crypto.com MCP API
- **AI-Powered Analysis**: Natural language market analysis using CrewAI and Gemini
- **A2A Communication**: Inter-agent messaging capabilities
- **FastAPI Server**: Modern async HTTP API with comprehensive error handling
- **Property-Based Testing**: Comprehensive test suite with Hypothesis

## Project Structure

```
examples/mcp-agent/
├── __init__.py              # Package initialization
├── app.py                   # Main FastAPI application
├── config.py                # Configuration management
├── market_data.py           # MCP API integration
├── crewai_backend.py        # CrewAI backend adapter
├── a2a_handlers.py          # A2A communication handlers
├── requirements.txt         # Python dependencies
├── .env.example            # Environment configuration template
├── pytest.ini             # Test configuration
├── README.md               # This file
└── tests/
    ├── __init__.py
    └── test_config.py      # Configuration tests
```

## Setup

1. **Install Dependencies**:
   ```bash
   cd examples/mcp-agent
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

3. **Required Environment Variables**:
   - `GEMINI_API_KEY`: Google Gemini API key for AI processing
   - `MCP_API_KEY`: Crypto.com MCP API key (optional)
   - `CRONOS_FACILITATOR_URL`: Cronos payment facilitator endpoint
   - `AGENT_REGISTRY_ENDPOINT`: Agent registry for A2A communication

## Usage

### Running the Agent

```bash
python app.py
```

The agent will start on `http://localhost:8002` by default.

### API Endpoints

- `GET /health`: Health check and service status
- `POST /chat`: Market data queries (requires x402 payment)
- `POST /a2a/send`: Send messages to other agents
- `POST /a2a/receive`: Receive messages from other agents

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run property-based tests only
pytest -k "test_sdk_integration_consistency"
```

## Configuration

The agent uses a hierarchical configuration system:

- **MCPConfig**: MCP API settings and timeouts
- **PaymentConfig**: x402 payment and token settings
- **CrewAIConfig**: AI backend configuration
- **A2AConfig**: Agent-to-agent communication settings
- **ServerConfig**: FastAPI server configuration

All configurations can be overridden via environment variables.

## Development Status

This is a work-in-progress implementation following the spec-driven development methodology. Current implementation status:

- ✅ Task 1: Project structure and configuration
- ⏳ Task 2: MCP API integration (placeholder)
- ⏳ Task 3: CrewAI backend (placeholder)
- ⏳ Task 4: A2A communication (placeholder)
- ⏳ Task 5: Payment integration (placeholder)
- ⏳ Task 6: Error handling and logging (placeholder)
- ⏳ Task 7: Comprehensive testing (in progress)

## Architecture

The agent follows a modular architecture with clear separation of concerns:

1. **FastAPI Layer**: HTTP endpoints and request handling
2. **Payment Layer**: x402 payment verification via 0rca-agent-sdk
3. **Data Layer**: MCP API integration and response parsing
4. **AI Layer**: CrewAI backend for natural language processing
5. **Communication Layer**: A2A protocol for inter-agent messaging
6. **Persistence Layer**: SQLite database via SDK

## Contributing

This example follows the 0rca-agent-sdk patterns and serves as a reference implementation. When contributing:

1. Follow the existing code structure and patterns
2. Add comprehensive tests for new functionality
3. Update documentation for any configuration changes
4. Ensure all property-based tests pass

## License

This project is part of the 0rca-agent-sdk examples and follows the same license terms.