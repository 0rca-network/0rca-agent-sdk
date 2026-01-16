const { expect } = require("chai");
const { ethers } = require("hardhat");

describe("TaskEscrow", function () {
    let TaskEscrow, taskEscrow;
    let MockUSDC, usdc;
    let IdentityRegistry, identityRegistry;
    let owner, orchestrator, agentOwner, user;
    let agentId = 1;

    beforeEach(async function () {
        [owner, orchestrator, agentOwner, user] = await ethers.getSigners();

        // Deploy Mock USDC
        MockUSDC = await ethers.getContractFactory("MockUSDC");
        usdc = await MockUSDC.deploy();
        await usdc.waitForDeployment();

        // Deploy Identity Registry
        IdentityRegistry = await ethers.getContractFactory("IdentityRegistry");
        identityRegistry = await IdentityRegistry.deploy(); // No args
        await identityRegistry.waitForDeployment();

        // Create Agent Identity
        // Register agent for agentOwner.
        // Connect as agentOwner to register, so owner is agentOwner.
        const tx = await identityRegistry.connect(agentOwner).register();
        await tx.wait();

        // _lastId starts at 0, returns value then increments. So first is 0.
        agentId = 0;

        // Deploy TaskEscrow
        TaskEscrow = await ethers.getContractFactory("TaskEscrow");
        taskEscrow = await TaskEscrow.deploy(
            await usdc.getAddress(),
            await identityRegistry.getAddress(),
            owner.address, // Treasury
            100 // 1% Fee
        );
        await taskEscrow.waitForDeployment();

        // Mint USDC to Orchestrator (User funds flow via Orchestrator in x402 usually)
        await usdc.mint(orchestrator.address, ethers.parseUnits("1000", 6));
        await usdc.connect(orchestrator).approve(await taskEscrow.getAddress(), ethers.parseUnits("1000", 6));
    });

    it("Should create a task", async function () {
        const taskId = ethers.keccak256(ethers.toUtf8Bytes("task-1"));
        const budget = ethers.parseUnits("100", 6);

        await expect(taskEscrow.connect(orchestrator).createTask(taskId, budget, user.address))
            .to.emit(taskEscrow, "TaskCreated")
            .withArgs(taskId, user.address, budget);

        const task = await taskEscrow.tasks(taskId);
        expect(task.budget).to.equal(budget);
        expect(task.remaining).to.equal(budget);
        expect(task.creator).to.equal(user.address);
        expect(task.status).to.equal(0); // Open
    });

    it("Should allow agent owner to spend budget", async function () {
        const taskId = ethers.keccak256(ethers.toUtf8Bytes("task-1"));
        const budget = ethers.parseUnits("100", 6);
        await taskEscrow.connect(orchestrator).createTask(taskId, budget, user.address);

        const spendAmount = ethers.parseUnits("50", 6);

        // Spend
        await expect(taskEscrow.connect(agentOwner).spend(taskId, agentId, spendAmount))
            .to.emit(taskEscrow, "TaskSpent")
            .withArgs(taskId, agentId, spendAmount);

        const task = await taskEscrow.tasks(taskId);
        expect(task.remaining).to.equal(budget - spendAmount);

        // Check Earnings (minus 1% fee)
        const fee = (spendAmount * 100n) / 10000n;
        const earnings = spendAmount - fee;
        expect(await taskEscrow.agentEarnings(agentId)).to.equal(earnings);
    });

    it("Should prevent spending more than budget", async function () {
        const taskId = ethers.keccak256(ethers.toUtf8Bytes("task-1"));
        const budget = ethers.parseUnits("100", 6);
        await taskEscrow.connect(orchestrator).createTask(taskId, budget, user.address);

        const spendAmount = ethers.parseUnits("101", 6);

        await expect(taskEscrow.connect(agentOwner).spend(taskId, agentId, spendAmount))
            .to.be.revertedWith("Insufficient task budget");
    });

    it("Should allow agent to withdraw earnings", async function () {
        const taskId = ethers.keccak256(ethers.toUtf8Bytes("task-1"));
        const budget = ethers.parseUnits("100", 6);
        await taskEscrow.connect(orchestrator).createTask(taskId, budget, user.address);
        const spendAmount = ethers.parseUnits("50", 6);
        await taskEscrow.connect(agentOwner).spend(taskId, agentId, spendAmount);

        const fee = (spendAmount * 100n) / 10000n;
        const earnings = spendAmount - fee;

        const initialBalance = await usdc.balanceOf(agentOwner.address);

        await expect(taskEscrow.connect(agentOwner).withdraw(agentId))
            .to.emit(taskEscrow, "AgentPaid")
            .withArgs(agentId, agentOwner.address, earnings);

        const finalBalance = await usdc.balanceOf(agentOwner.address);
        expect(finalBalance - initialBalance).to.equal(earnings);
        expect(await taskEscrow.agentEarnings(agentId)).to.equal(0);
    });
});
