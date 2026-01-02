// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";

interface IERC20WithAuth is IERC20 {
    function transferWithAuthorization(
        address from,
        address to,
        uint256 value,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external;
}

interface IERC8004 is IERC721 {
    // ERC-8004 is built on 721, so ownerOf is standard.
    // We just need the interface to be clear.
}

contract AgentEscrow {
    IERC20WithAuth public immutable usdc;
    IERC8004 public immutable registry;
    address public immutable facilitator;

    mapping(uint256 => uint256) public balances; // agentId => amount

    event AgentCredited(uint256 indexed agentId, uint256 amount);
    event AgentWithdrawn(uint256 indexed agentId, address indexed to, uint256 amount);

    constructor(address _usdc, address _registry, address _facilitator) {
        require(_usdc != address(0), "Invalid USDC");
        require(_registry != address(0), "Invalid Registry");
        require(_facilitator != address(0), "Invalid Facilitator");
        
        usdc = IERC20WithAuth(_usdc);
        registry = IERC8004(_registry);
        facilitator = _facilitator;
    }

    modifier onlyFacilitator() {
        require(msg.sender == facilitator, "Only facilitator");
        _;
    }

    /**
     * @notice Credits an agent's balance by pulling tokens from a user via EIP-3009.
     * @dev Called ONLY by the off-chain facilitator after verifying the signature.
     */
    function creditAgent(
        uint256 agentId,
        uint256 amount,
        address from,
        uint256 validAfter,
        uint256 validBefore,
        bytes32 nonce,
        uint8 v,
        bytes32 r,
        bytes32 s
    ) external onlyFacilitator {
        // 1. Pull tokens from user to this contract
        usdc.transferWithAuthorization(
            from,
            address(this),
            amount,
            validAfter,
            validBefore,
            nonce,
            v,
            r,
            s
        );

        // 2. Update internal accounting
        balances[agentId] += amount;

        emit AgentCredited(agentId, amount);
    }

    /**
     * @notice Withdraws the full balance of an agent to its owner.
     * @param agentId The ID of the agent to withdraw for.
     */
    function withdraw(uint256 agentId) external {
        address owner = registry.ownerOf(agentId);
        require(msg.sender == owner, "Not agent owner");

        uint256 amount = balances[agentId];
        require(amount > 0, "No funds");

        balances[agentId] = 0;
        
        // Transfer USDC to the owner
        require(usdc.transfer(owner, amount), "Transfer failed");

        emit AgentWithdrawn(agentId, owner, amount);
    }
}
