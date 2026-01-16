import os

# Protocol Constants (Default: Cronos Testnet)
# These should be overridden by environment variables in production.

# CAIP
CHAIN_CAIP = os.getenv("CHAIN_CAIP", "eip155:338")

# --- REGISTRY SUITE ---
IDENTITY_REGISTRY = os.getenv("IDENTITY_REGISTRY", "0x58e67dEEEcde20f10eD90B5191f08f39e81B6658")
REPUTATION_REGISTRY = os.getenv("REPUTATION_REGISTRY", "0x87A0E38fF8e63AE90ea95bbd61Ce9c6EC75422d0")
VALIDATION_REGISTRY = os.getenv("VALIDATION_REGISTRY", "0x5163A9689C0560DE07Cdc2ecA391BA5BE8b3D35A")
AGENT_ESCROW = os.getenv("AGENT_ESCROW", "0x71be791E25abacA49FEaD19054FB044686c90c3b")
TASK_ESCROW = os.getenv("TASK_ESCROW", "0x482C45A341e6BE4D171136daba45E87ACaAc22a0")

# --- ASSETS ---
USDC_E = os.getenv("USDC_E", "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0")

# --- INFRASTRUCTURE ---
FACILITATOR_URL = os.getenv("FACILITATOR_URL", "https://facilitator.cronoslabs.org/v2/x402")
