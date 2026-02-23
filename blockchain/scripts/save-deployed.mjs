/**
 * save-deployed.mjs
 * Run this AFTER: npx hardhat ignition deploy ignition/modules/VerificationRegistry.ts --network amoy
 *
 * It reads Hardhat Ignition's deployment artifacts and writes deployed.json
 * with the contract address and ABI — ready for the backend to use.
 *
 * Usage:
 *   node scripts/save-deployed.mjs [chainId]
 *   node scripts/save-deployed.mjs 80002        # Polygon Amoy (default)
 *   node scripts/save-deployed.mjs 137          # Polygon Mainnet
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, "..");

// ── Args ─────────────────────────────────────────────────────────────────────
const chainId = process.argv[2] ?? "80002"; // Amoy by default
const networkName = chainId === "137" ? "polygon" : "amoy";

// ── 1. Read deployed address from Ignition ───────────────────────────────────
const ignitionDir = path.join(root, "ignition", "deployments", `chain-${chainId}`);
const addressFile = path.join(ignitionDir, "deployed_addresses.json");

if (!fs.existsSync(addressFile)) {
    console.error(`❌ Ignition deployment not found at:\n   ${addressFile}`);
    console.error(`   Make sure you ran:\n   npx hardhat ignition deploy ignition/modules/VerificationRegistry.ts --network ${networkName}`);
    process.exit(1);
}

const addresses = JSON.parse(fs.readFileSync(addressFile, "utf-8"));
// Ignition key format: "ModuleName#ContractName"
const addrKey = Object.keys(addresses).find((k) =>
    k.includes("VerificationRegistry")
);
if (!addrKey) {
    console.error("❌ VerificationRegistry not found in deployed_addresses.json");
    console.error("   Keys found:", Object.keys(addresses));
    process.exit(1);
}
const address = addresses[addrKey];
console.log(`✅ Contract address: ${address}`);

// ── 2. Read ABI from compiled artifacts ──────────────────────────────────────
const artifactPath = path.join(
    root,
    "artifacts",
    "contracts",
    "VerificationRegistry.sol",
    "VerificationRegistry.json"
);

if (!fs.existsSync(artifactPath)) {
    console.error(`❌ Artifact not found at:\n   ${artifactPath}`);
    console.error("   Run: npx hardhat compile");
    process.exit(1);
}

const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf-8"));

// ── 3. Write deployed.json ────────────────────────────────────────────────────
const output = {
    network: networkName,
    chainId: Number(chainId),
    contractName: "VerificationRegistry",
    address,
    abi: artifact.abi,
    deployedAt: new Date().toISOString(),
};

const outPath = path.join(root, "deployed.json");
fs.writeFileSync(outPath, JSON.stringify(output, null, 2));

console.log(`📄 deployed.json saved to: ${outPath}`);
console.log(`🔗 Polygonscan Amoy: https://amoy.polygonscan.com/address/${address}`);
