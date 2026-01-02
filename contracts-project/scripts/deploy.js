const hre = require("hardhat");

async function main() {
    const [deployer] = await hre.ethers.getSigners();

    console.log("Deploying contracts with the account:", deployer.address);

    // 1. Deploy Mocks
    const MockUSDC = await hre.ethers.getContractFactory("MockUSDC");
    const usdc = await MockUSDC.deploy();
    await usdc.waitForDeployment();
    const usdcAddress = await usdc.getAddress();
    console.log("MockUSDC deployed to:", usdcAddress);

    const MockERC8004 = await hre.ethers.getContractFactory("MockERC8004");
    const registry = await MockERC8004.deploy();
    await registry.waitForDeployment();
    const registryAddress = await registry.getAddress();
    console.log("MockERC8004 deployed to:", registryAddress);

    // 2. Deploy AgentEscrow
    // Initial facilitator is the deployer for testing convenience
    const facilitator = deployer.address;

    const AgentEscrow = await hre.ethers.getContractFactory("AgentEscrow");
    const escrow = await AgentEscrow.deploy(
        usdcAddress,
        registryAddress,
        facilitator
    );
    await escrow.waitForDeployment();
    const escrowAddress = await escrow.getAddress();
    console.log("AgentEscrow deployed to:", escrowAddress);

    // 3. Setup (optional but helpful)
    // Mint a dummy agent for testing withdraw
    // Agent ID 1 owned by deployer
    await registry.mint(deployer.address, 1);
    console.log("Minted Agent 1 to deployer");
}

main()
    .then(() => process.exit(0))
    .catch((error) => {
        console.error(error);
        process.exit(1);
    });
