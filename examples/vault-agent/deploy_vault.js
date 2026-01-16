const { ethers } = require("hardhat");
const fs = require("fs");
const path = require("path");

async function main() {
    console.log("Deploying OrcaAgentVault...");

    // 1. Setup Constants
    const USDC_TOKEN = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0";
    const AGENT_ID = 0; // The ID you registered/will register in IdentityRegistry
    const OWNER = "0x975C5b75Ff1141E10c4f28454849894F766B945E"; // Your developer wallet
    const AGENT = "0x975C5b75Ff1141E10c4f28454849894F766B945E"; // Your agent wallet

    // 2. Deploy
    const Vault = await ethers.getContractFactory("OrcaAgentVault");
    const vault = await Vault.deploy(USDC_TOKEN, AGENT_ID, OWNER, AGENT);
    await vault.waitForDeployment();

    const vaultAddress = await vault.getAddress();
    console.log("-----------------------------------------");
    console.log("VAULT DEPLOYED TO:", vaultAddress);
    console.log("AGENT ID:", AGENT_ID);
    console.log("OWNER:", OWNER);
    console.log("-----------------------------------------");

    // 3. Save to env for easy access
    fs.writeFileSync(".env.vault", `AGENT_VAULT=${vaultAddress}\nAGENT_ID=${AGENT_ID}\n`);
}

main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
});
