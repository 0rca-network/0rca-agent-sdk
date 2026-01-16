const { ethers, network } = require("hardhat");

async function main() {
    console.log("Deploying TaskEscrow to:", network.name);

    let identityRegistryAddress;
    let usdcAddress;
    let treasuryAddress;

    if (network.name === "cronosTestnet") {
        identityRegistryAddress = "0x58e67dEEEcde20f10eD90B5191f08f39e81B6658";
        usdcAddress = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0";
        // Use a default treasury or the deployer
        const [deployer] = await ethers.getSigners();
        treasuryAddress = deployer.address;
        console.log("Using existing contracts for Cronos Testnet");
    } else {
        // Local deployment - deploy mocks
        const [deployer] = await ethers.getSigners();
        treasuryAddress = deployer.address;

        console.log("Deploying Mocks...");

        const MockUSDC = await ethers.getContractFactory("MockUSDC");
        const usdc = await MockUSDC.deploy();
        await usdc.waitForDeployment();
        usdcAddress = await usdc.getAddress();
        console.log("MockUSDC deployed to:", usdcAddress);

        const IdentityRegistry = await ethers.getContractFactory("IdentityRegistry");
        const identityRegistry = await IdentityRegistry.deploy();
        await identityRegistry.waitForDeployment();
        identityRegistryAddress = await identityRegistry.getAddress();
        console.log("IdentityRegistry deployed to:", identityRegistryAddress);
    }

    // Deploy Escrow
    const TaskEscrow = await ethers.getContractFactory("TaskEscrow");
    const taskEscrow = await TaskEscrow.deploy(
        usdcAddress,
        identityRegistryAddress,
        treasuryAddress,
        100 // 1% Fee
    );
    await taskEscrow.waitForDeployment();

    console.log("TaskEscrow deployed to:", await taskEscrow.getAddress());
    console.log("----------------------------------------------------");
    console.log(`export TASK_ESCROW="${await taskEscrow.getAddress()}"`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
