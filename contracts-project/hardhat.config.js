require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
    solidity: {
        version: "0.8.28",
        settings: {
            optimizer: {
                enabled: true,
                runs: 200,
            },
            viaIR: true,
        },
    },
    networks: {
        ganache: {
            url: "http://127.0.0.1:8545",
            chainId: 1337
        },
        localhost: {
            url: "http://127.0.0.1:8545",
            chainId: 31337
        },
        cronosTestnet: {
            url: "https://evm-t3.cronos.org",
            chainId: 338,
            accounts: process.env.PRIVATE_KEY ? [process.env.PRIVATE_KEY] : [],
        }
    }
};
