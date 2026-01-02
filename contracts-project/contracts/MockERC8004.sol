// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";

contract MockERC8004 is ERC721 {
    constructor() ERC721("AgentRegistry", "AGENT") {}

    function mint(address to, uint256 agentId) external {
        _mint(to, agentId);
    }
}
