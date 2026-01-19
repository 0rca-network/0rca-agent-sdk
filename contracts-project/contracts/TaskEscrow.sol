// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IIdentityRegistry {
    function ownerOf(uint256 agentId) external view returns (address);
}

interface IAgentEscrow {
    function deposit(uint256 agentId, uint256 amount) external;
}

contract TaskEscrow is Ownable, ReentrancyGuard {
    IERC20 public immutable paymentToken;
    IIdentityRegistry public immutable identityRegistry;
    IAgentEscrow public agentEscrow;

    struct Task {
        uint256 budget;
        uint256 remaining;
        address creator;
        TaskStatus status;
        bool exists;
    }

    enum TaskStatus { Open, Closed }

    mapping(bytes32 => Task) public tasks;
    
    address public platformTreasury;
    uint256 public platformFeeBps; // 100 = 1%

    event TaskCreated(bytes32 indexed taskId, address indexed creator, uint256 budget);
    event TaskSpent(bytes32 indexed taskId, uint256 indexed agentId, uint256 amount);
    event TaskClosed(bytes32 indexed taskId, uint256 refundAmount);
    event TreasuryUpdated(address newTreasury, uint256 newFeeBps);
    event AgentEscrowUpdated(address newEscrow);

    constructor(
        address _paymentToken,
        address _identityRegistry,
        address _platformTreasury,
        uint256 _platformFeeBps
    ) Ownable(msg.sender) {
        paymentToken = IERC20(_paymentToken);
        identityRegistry = IIdentityRegistry(_identityRegistry);
        platformTreasury = _platformTreasury;
        platformFeeBps = _platformFeeBps;
    }

    function setAgentEscrow(address _agentEscrow) external onlyOwner {
        agentEscrow = IAgentEscrow(_agentEscrow);
        emit AgentEscrowUpdated(_agentEscrow);
    }

    function setTreasury(address _platformTreasury, uint256 _platformFeeBps) external onlyOwner {
        platformTreasury = _platformTreasury;
        platformFeeBps = _platformFeeBps;
        emit TreasuryUpdated(_platformTreasury, _platformFeeBps);
    }

    function createTask(bytes32 taskId, uint256 budget, address user) external nonReentrant {
        require(!tasks[taskId].exists, "Task already exists");
        require(paymentToken.transferFrom(msg.sender, address(this), budget), "Transfer failed");

        tasks[taskId] = Task({
            budget: budget,
            remaining: budget,
            creator: user,
            status: TaskStatus.Open,
            exists: true
        });

        emit TaskCreated(taskId, user, budget);
    }

    function spend(bytes32 taskId, uint256 agentId, uint256 amount) external nonReentrant {
        Task storage task = tasks[taskId];
        require(task.exists && task.status == TaskStatus.Open, "Invalid task");
        require(task.remaining >= amount, "Insufficient budget");
        
        address agentOwner = identityRegistry.ownerOf(agentId);
        require(msg.sender == agentOwner, "Only the agent owner can spend");

        task.remaining -= amount;

        uint256 fee = (amount * platformFeeBps) / 10000;
        uint256 netAmount = amount - fee;

        if (fee > 0) {
            require(paymentToken.transfer(platformTreasury, fee), "Treasury transfer failed");
        }
        
        // Payout to AgentEscrow Vault
        if (address(agentEscrow) != address(0)) {
            require(paymentToken.approve(address(agentEscrow), netAmount), "Approval failed");
            agentEscrow.deposit(agentId, netAmount);
        } else {
            // Fallback to direct payment if no vault configured
            require(paymentToken.transfer(agentOwner, netAmount), "Direct payment failed");
        }

        emit TaskSpent(taskId, agentId, amount);
    }

    function closeTask(bytes32 taskId) external nonReentrant {
        Task storage task = tasks[taskId];
        require(task.exists && task.status == TaskStatus.Open, "Invalid task");
        require(msg.sender == task.creator, "Only creator can close");

        uint256 refund = task.remaining;
        task.status = TaskStatus.Closed;
        task.remaining = 0;

        if (refund > 0) {
            require(paymentToken.transfer(task.creator, refund), "Refund failed");
        }

        emit TaskClosed(taskId, refund);
    }
}
