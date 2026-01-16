$pk = (Get-Content ..\agent_identity.json | ConvertFrom-Json).private_key
if (!$pk.StartsWith("0x")) { $pk = "0x" + $pk }
$env:PRIVATE_KEY = $pk
npx hardhat run scripts/deploy_vault.js --network cronosTestnet
