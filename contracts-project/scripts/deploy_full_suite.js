const hre = require("hardhat");

async function main() {
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying Full ERC-8004 Suite with account:", deployer.address);

    const USDC_E = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1";

    // 1. IdentityRegistry
    console.log("\n1. Deploying IdentityRegistry...");
    const IdentityRegistry = await hre.ethers.getContractFactory("IdentityRegistry");
    const identity = await IdentityRegistry.deploy();
    await identity.waitForDeployment();
    const identityAddress = await identity.getAddress();
    console.log("-> IdentityRegistry:", identityAddress);

    // 2. ReputationRegistry (Needs Identity)
    console.log("\n2. Deploying ReputationRegistry...");
    const ReputationRegistry = await hre.ethers.getContractFactory("ReputationRegistry");
    const reputation = await ReputationRegistry.deploy(identityAddress);
    await reputation.waitForDeployment();
    console.log("-> ReputationRegistry:", await reputation.getAddress());

    // 3. ValidationRegistry (Needs Identity)
    console.log("\n3. Deploying ValidationRegistry...");
    const ValidationRegistry = await hre.ethers.getContractFactory("ValidationRegistry");
    const validation = await ValidationRegistry.deploy(identityAddress);
    await validation.waitForDeployment();
    console.log("-> ValidationRegistry:", await validation.getAddress());

    // 4. AgentEscrow (Needs USDC, Identity, Facilitator as Deployer)
    console.log("\n4. Deploying AgentEscrow...");
    const AgentEscrow = await hre.ethers.getContractFactory("AgentEscrow");
    const escrow = await AgentEscrow.deploy(
        USDC_E,
        identityAddress,
        deployer.address // Initial facilitator is deployer
    );
    await escrow.waitForDeployment();
    const escrowAddress = await escrow.getAddress();
    console.log("-> AgentEscrow:", escrowAddress);

    // 5. Setup: Register Agent 0
    console.log("\n5. Registering Genesis Agent (ID 0)...");
    const tx = await identity.register();
    await tx.wait();
    console.log("-> Agent 0 registered to", deployer.address);

    console.log("\n--- FINAL DEPLOYMENT REPORT (COPY THESE TO SDK) ---");
    console.log("IDENTITY_REGISTRY =", `"${identityAddress}"`);
    console.log("REPUTATION_REGISTRY =", `"${await reputation.getAddress()}"`);
    console.log("VALIDATION_REGISTRY =", `"${await validation.getAddress()}"`);
    console.log("AGENT_ESCROW =", `"${escrowAddress}"`);
    console.log("USDC_E =", `"${USDC_E}"`);
    console.log("---------------------------------------------------");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
