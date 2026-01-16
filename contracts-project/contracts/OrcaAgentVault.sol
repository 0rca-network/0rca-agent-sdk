// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title OrcaAgentVault
 * @dev A sovereign contract for a single AI Agent. 
 * Handles its own tasks, earnings, and withdrawals.
 */
contract OrcaAgentVault is Ownable, ReentrancyGuard {
    IERC20 public immutable paymentToken;
    uint256 public immutable agentId;
    address public agent;

    struct Task {
        uint256 budget;
        uint256 remaining;
        address creator;
        bool exists;
        bool closed;
    }

    mapping(bytes32 => Task) public tasks;
    uint256 public accumulatedEarnings;

    event TaskCreated(bytes32 indexed taskId, address indexed creator, uint256 budget);
    event TaskSpent(bytes32 indexed taskId, uint256 amount);
    event TaskClosed(bytes32 indexed taskId, uint256 refundAmount);
    event EarningsWithdrawn(address indexed owner, uint256 amount);

    constructor(address _paymentToken, uint256 _agentId, address _owner, address _agent) Ownable(_owner) {
        paymentToken = IERC20(_paymentToken);
        agentId = _agentId;
        agent = _agent;
    }

    modifier onlyAuthorized() {
        require(msg.sender == owner() || msg.sender == agent, "Not owner or agent");
        _;
    }

    /**
     * @dev User funds a task specifically for this agent.
     */
    function createTask(bytes32 taskId, uint256 budget) external nonReentrant {
        require(!tasks[taskId].exists, "Task exists");
        require(paymentToken.transferFrom(msg.sender, address(this), budget), "Transfer failed");

        tasks[taskId] = Task({
            budget: budget,
            remaining: budget,
            creator: msg.sender,
            exists: true,
            closed: false
        });

        emit TaskCreated(taskId, msg.sender, budget);
    }

    /**
     * @dev Agent claims budget from a task.
     * Moves funds from task bucket to agent balance.
     */
    function spend(bytes32 taskId, uint256 amount) external onlyAuthorized nonReentrant {
        Task storage task = tasks[taskId];
        require(task.exists && !task.closed, "Invalid task");
        require(task.remaining >= amount, "Insufficient budget");

        task.remaining -= amount;
        accumulatedEarnings += amount;

        emit TaskSpent(taskId, amount);
    }

    /**
     * @dev Developer (as Owner) withdraws accumulated earnings.
     */
    function withdraw() external onlyOwner nonReentrant {
        uint256 amount = accumulatedEarnings;
        require(amount > 0, "No earnings");

        accumulatedEarnings = 0;
        require(paymentToken.transfer(owner(), amount), "Transfer failed");

        emit EarningsWithdrawn(owner(), amount);
    }

    /**
     * @dev User can close task to get refund of remaining budget.
     */
    function closeTask(bytes32 taskId) external nonReentrant {
        Task storage task = tasks[taskId];
        require(task.exists && !task.closed, "Invalid task");
        require(msg.sender == task.creator, "Not creator");

        uint256 refund = task.remaining;
        task.closed = true;
        task.remaining = 0;

        if (refund > 0) {
            require(paymentToken.transfer(task.creator, refund), "Refund failed");
        }

        emit TaskClosed(taskId, refund);
    }
}
