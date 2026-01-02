require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
    solidity: "0.8.28",
    networks: {
        ganache: {
            url: "http://127.0.0.1:8545",
            chainId: 1337
        },
        // Add localhost explicit config if needed, but default works usually. 
        // Hardhat Node uses 31337
        localhost: {
            url: "http://127.0.0.1:8545",
            chainId: 31337
        }
    }
};
