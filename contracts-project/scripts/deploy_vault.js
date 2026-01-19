const { ethers, network } = require("hardhat");

async function main() {
    console.log("Starting Vault Architecture Deployment on:", network.name);
    const [deployer] = await ethers.getSigners();
    console.log("Deployer:", deployer.address);

    const IDENTITY_REGISTRY = "0x58e67dEEEcde20f10eD90B5191f08f39e81B6658";
    const USDC_TOKEN = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1";
    const PLATFORM_TREASURY = deployer.address;

    // 1. Deploy AgentEscrow (The Vault)
    console.log("\n--- Step 1: Deploying AgentEscrow ---");
    const AgentEscrow = await ethers.getContractFactory("AgentEscrow");
    const agentEscrow = await AgentEscrow.deploy(USDC_TOKEN, IDENTITY_REGISTRY);
    await agentEscrow.waitForDeployment();
    const agentEscrowAddress = await agentEscrow.getAddress();
    console.log("AgentEscrow deployed to:", agentEscrowAddress);

    // 2. Deploy TaskEscrow
    console.log("\n--- Step 2: Deploying TaskEscrow ---");
    const TaskEscrow = await ethers.getContractFactory("TaskEscrow");
    const taskEscrow = await TaskEscrow.deploy(
        USDC_TOKEN,
        IDENTITY_REGISTRY,
        PLATFORM_TREASURY,
        100 // 1%
    );
    await taskEscrow.waitForDeployment();
    const taskEscrowAddress = await taskEscrow.getAddress();
    console.log("TaskEscrow deployed to:", taskEscrowAddress);

    // 3. Link them & Authorize
    console.log("\n--- Step 3: Configuring Liaison ---");

    // TaskEscrow needs to know where the vault is
    await taskEscrow.setAgentEscrow(agentEscrowAddress);
    console.log("Linked TaskEscrow to Vault.");

    // AgentEscrow needs to authorize TaskEscrow to deposit
    await agentEscrow.setAuthorizedPayer(taskEscrowAddress, true);
    console.log("Authorized TaskEscrow in Vault.");

    console.log("\nDEPLOYMENT COMPLETE");
    console.log("-----------------------------------------");
    console.log(`export AGENT_ESCROW="${agentEscrowAddress}"`);
    console.log(`export TASK_ESCROW="${taskEscrowAddress}"`);
    console.log("-----------------------------------------");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
