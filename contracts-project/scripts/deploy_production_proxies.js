const hre = require("hardhat");

async function main() {
    const [deployer] = await hre.ethers.getSigners();
    console.log("Deploying Production Proxied Suite with:", deployer.address);

    const USDC_E = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1";

    // Helper to deploy proxy
    async function deployProxy(factoryName, initializeArgs = []) {
        // 1. Implementation
        const Factory = await hre.ethers.getContractFactory(factoryName);
        const impl = await Factory.deploy();
        await impl.waitForDeployment();
        const implAddress = await impl.getAddress();
        console.log(`- ${factoryName} Implementation: ${implAddress}`);

        // 2. Proxy
        const iface = Factory.interface;
        const initData = iface.encodeFunctionData("initialize", initializeArgs);

        const Proxy = await hre.ethers.getContractFactory("contracts/ERC1967Proxy.sol:ERC1967Proxy");
        const proxy = await Proxy.deploy(implAddress, initData);
        await proxy.waitForDeployment();
        const proxyAddress = await proxy.getAddress();
        console.log(`- ${factoryName} Proxy: ${proxyAddress}`);

        return proxyAddress;
    }

    // 1. IdentityRegistry Proxy
    console.log("\n1. Deploying IdentityRegistry Proxy...");
    const identityProxy = await deployProxy("IdentityRegistryUpgradeable", []);

    // 2. ReputationRegistry Proxy
    console.log("\n2. Deploying ReputationRegistry Proxy...");
    const reputationProxy = await deployProxy("ReputationRegistryUpgradeable", [identityProxy]);

    // 3. ValidationRegistry Proxy
    console.log("\n3. Deploying ValidationRegistry Proxy...");
    const validationProxy = await deployProxy("ValidationRegistryUpgradeable", [identityProxy]);

    // 4. AgentEscrow (Regular, linked to Identity Proxy)
    console.log("\n4. Deploying AgentEscrow...");
    const AgentEscrow = await hre.ethers.getContractFactory("AgentEscrow");
    const escrow = await AgentEscrow.deploy(
        USDC_E,
        identityProxy,
        deployer.address
    );
    await escrow.waitForDeployment();
    const escrowAddress = await escrow.getAddress();
    console.log("-> AgentEscrow:", escrowAddress);

    // 5. Register Agent 0 on Proxy
    console.log("\n5. Registering Agent 0 on Proxy...");
    const identity = await hre.ethers.getContractAt("IdentityRegistryUpgradeable", identityProxy);
    const tx = await identity.register();
    await tx.wait();
    console.log("-> Agent 0 registered!");

    console.log("\n--- PRODUCTION DEPLOYMENT REPORT (PROXIES) ---");
    console.log("IDENTITY_REGISTRY =", `"${identityProxy}"`);
    console.log("REPUTATION_REGISTRY =", `"${reputationProxy}"`);
    console.log("VALIDATION_REGISTRY =", `"${validationProxy}"`);
    console.log("AGENT_ESCROW =", `"${escrowAddress}"`);
    console.log("USDC_E =", `"${USDC_E}"`);
    console.log("----------------------------------------------");
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
