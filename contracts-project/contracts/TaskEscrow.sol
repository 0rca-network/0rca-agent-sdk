// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

interface IIdentityRegistry {
    function ownerOf(uint256 tokenId) external view returns (address);
}

contract TaskEscrow is Ownable, ReentrancyGuard {
    
    IERC20 public immutable paymentToken;
    IIdentityRegistry public immutable identityRegistry;
    address public platformTreasury;
    uint256 public platformFeeBps; // Basis points (e.g., 100 = 1%)

    enum TaskStatus { Open, Closed }

    struct Task {
        uint256 budget;
        uint256 remaining;
        address creator;
        TaskStatus status;
        bool exists;
    }

    // taskId => Task
    mapping(bytes32 => Task) public tasks;
    
    // agentId => earnings
    mapping(uint256 => uint256) public agentEarnings;

    event TaskCreated(bytes32 indexed taskId, address indexed creator, uint256 budget);
    event TaskSpent(bytes32 indexed taskId, uint256 indexed agentId, uint256 amount);
    event AgentPaid(uint256 indexed agentId, address indexed payee, uint256 amount);
    event TaskClosed(bytes32 indexed taskId, uint256 refundAmount);
    event TreasuryUpdated(address newTreasury, uint256 newFeeBps);

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

    // --- Task Lifecycle ---

    function createTask(bytes32 taskId, uint256 budget, address user) external {
        require(!tasks[taskId].exists, "Task already exists");
        require(budget > 0, "Budget must be > 0");
        
        // Transfer funds from msg.sender (Orchestrator/Relayer must have allowance from User, 
        // OR Orchestrator funds it itself after x402 verification)
        // Ideally: User -> Orchestrator (x402) -> TaskEscrow (createTask)
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
        require(task.exists, "Task does not exist");
        require(task.status == TaskStatus.Open, "Task is closed");
        require(amount <= task.remaining, "Insufficient task budget");
        require(amount > 0, "Amount must be > 0");

        // Verify Caller using IdentityRegistry
        // Only the owner of the Agent NFT can claim payment for that agent
        address agentOwner = identityRegistry.ownerOf(agentId);
        require(msg.sender == agentOwner, "Not agent owner");

        task.remaining -= amount;
        
        // Calculate Fee
        uint256 fee = (amount * platformFeeBps) / 10000;
        uint256 earnings = amount - fee;

        // Assign Earnings
        agentEarnings[agentId] += earnings;

        // Send Fee Immediately (or accumulate, but immediate is simpler for treasury)
        if (fee > 0 && platformTreasury != address(0)) {
            require(paymentToken.transfer(platformTreasury, fee), "Fee transfer failed");
        }

        emit TaskSpent(taskId, agentId, amount);
    }

    function closeTask(bytes32 taskId) external nonReentrant {
        Task storage task = tasks[taskId];
        require(task.exists, "Task does not exist");
        require(task.status == TaskStatus.Open, "Task already closed");
        
        // Only creator can close (or add an Admin override if needed)
        // In the x402 flow, the Orchestrator (who called createTask) might need to be the one to close it,
        // or the 'creator' field which is the User address. 
        // Let's allow the stored 'creator' OR the contract owner (Orchestrator fallback).
        require(msg.sender == task.creator || msg.sender == owner(), "Not authorized");

        task.status = TaskStatus.Closed;
        uint256 refund = task.remaining;

        if (refund > 0) {
            task.remaining = 0;
            require(paymentToken.transfer(task.creator, refund), "Refund failed");
        }

        emit TaskClosed(taskId, refund);
    }

    // --- Agent Withdrawals ---

    function withdraw(uint256 agentId) external nonReentrant {
        uint256 amount = agentEarnings[agentId];
        require(amount > 0, "No earnings");

        address agentOwner = identityRegistry.ownerOf(agentId);
        require(msg.sender == agentOwner, "Not agent owner");

        agentEarnings[agentId] = 0;
        require(paymentToken.transfer(agentOwner, amount), "Transfer failed");

        emit AgentPaid(agentId, agentOwner, amount);
    }

    // --- Admin ---

    function setTreasury(address _platformTreasury, uint256 _platformFeeBps) external onlyOwner {
        platformTreasury = _platformTreasury;
        platformFeeBps = _platformFeeBps;
        emit TreasuryUpdated(_platformTreasury, _platformFeeBps);
    }
}
