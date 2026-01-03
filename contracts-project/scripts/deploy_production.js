const hre = require("hardhat");

async function main() {
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying production-ready contracts with:", deployer.address);

    // Cronos Testnet USDC.e
    const USDC_E = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0";

    // 1. Deploy IdentityRegistry
    console.log("Deploying IdentityRegistry...");
    const IdentityRegistry = await hre.ethers.getContractFactory("IdentityRegistry");
    const registry = await IdentityRegistry.deploy();
    await registry.waitForDeployment();
    const registryAddress = await registry.getAddress();
    console.log("IdentityRegistry deployed to:", registryAddress);

    // 2. Deploy AgentEscrow
    // Set the deployer as the initial facilitator for testing
    console.log("Deploying AgentEscrow...");
    const AgentEscrow = await hre.ethers.getContractFactory("AgentEscrow");
    const escrow = await AgentEscrow.deploy(
        USDC_E,
        registryAddress,
        deployer.address // facilitator
    );
    await escrow.waitForDeployment();
    const escrowAddress = await escrow.getAddress();
    console.log("AgentEscrow deployed to:", escrowAddress);

    // 3. Register our Gemini Agent
    console.log("Registering Gemini Agent (ID 0)...");
    const tx = await registry.register();
    await tx.wait();
    console.log("Agent registered! ID: 0 (owned by " + deployer.address + ")");

    console.log("\n--- DEPLOYMENT SUMMARY ---");
    console.log("Registry:", registryAddress);
    console.log("Escrow:", escrowAddress);
    console.log("USDC.E:", USDC_E);
    console.log("Owner/Facilitator:", deployer.address);
    console.log("Agent ID: 0");
    console.log("--------------------------");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
