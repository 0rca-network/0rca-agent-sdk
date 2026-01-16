// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IIdentityRegistry {
    function getAgentOwner(uint256 agentId) external view returns (address);
}

/**
 * @title AgentEscrow
 * @dev Centralized vault for all agent earnings (x402 + TaskEscrow).
 */
contract AgentEscrow is Ownable, ReentrancyGuard {
    IERC20 public immutable paymentToken;
    IIdentityRegistry public immutable identityRegistry;

    // agentId => earnings
    mapping(uint256 => uint256) public agentEarnings;
    
    // Whitelist for contracts allowed to deposit (TaskEscrow, Facilitator)
    mapping(address => bool) public authorizedPayers;

    event EarningsDeposited(uint256 indexed agentId, address indexed payer, uint256 amount);
    event EarningsWithdrawn(uint256 indexed agentId, address indexed owner, uint256 amount);
    event PayerAuthorized(address indexed payer, bool status);

    constructor(address _paymentToken, address _identityRegistry) Ownable(msg.sender) {
        paymentToken = IERC20(_paymentToken);
        identityRegistry = IIdentityRegistry(_identityRegistry);
    }

    modifier onlyAuthorized() {
        require(authorizedPayers[msg.sender] || msg.sender == owner(), "Not authorized to deposit");
        _;
    }

    function setAuthorizedPayer(address _payer, bool _status) external onlyOwner {
        authorizedPayers[_payer] = _status;
        emit PayerAuthorized(_payer, _status);
    }

    /**
     * @dev Called by TaskEscrow or Facilitator to credit an agent.
     * The USDC must be transferred to this contract before calling this.
     */
    function deposit(uint256 agentId, uint256 amount) external nonReentrant onlyAuthorized {
        require(amount > 0, "Amount must be > 0");
        
        // This contract must have received the tokens already (via transfer/transferFrom)
        // or we can use transferFrom here if approved. 
        // For simplicity with TaskEscrow, TaskEscrow will transfer USDC and then call this.
        
        agentEarnings[agentId] += amount;
        emit EarningsDeposited(agentId, msg.sender, amount);
    }

    /**
     * @dev Allows the agent's owner to withdraw their accumulated earnings.
     */
    function withdraw(uint256 agentId) external nonReentrant {
        address owner = identityRegistry.getAgentOwner(agentId);
        require(msg.sender == owner, "Only the agent owner can withdraw");
        
        uint256 amount = agentEarnings[agentId];
        require(amount > 0, "No earnings to withdraw");

        agentEarnings[agentId] = 0;
        require(paymentToken.transfer(owner, amount), "Transfer failed");

        emit EarningsWithdrawn(agentId, owner, amount);
    }
}
