/**
 * deploy.ts — Deploys VerificationRegistry to Polygon Amoy testnet.
 *
 * Usage:
 *   npx hardhat run scripts/deploy.ts --network amoy
 *
 * After running, the contract address and ABI are saved to:
 *   ../deployed.json
 */

import hre from "hardhat";
import fs from "fs";
import path from "path";

async function main() {
    console.log("🚀 Deploying VerificationRegistry...");
    console.log(`   Network: ${hre.network.name}`);

    // Deploy the contract
    const registry = await hre.viem.deployContract("VerificationRegistry");

    const address = registry.address;
    console.log(`✅ VerificationRegistry deployed at: ${address}`);

    // Read the compiled ABI from the Hardhat artifacts
    const artifactPath = path.join(
        __dirname,
        "../artifacts/contracts/VerificationRegistry.sol/VerificationRegistry.json"
    );

    if (!fs.existsSync(artifactPath)) {
        throw new Error(
            "Artifact not found. Run `npx hardhat compile` first.\n" +
            `Expected at: ${artifactPath}`
        );
    }

    const artifact = JSON.parse(fs.readFileSync(artifactPath, "utf-8"));

    // Save deployed.json to blockchain root
    const deployedData = {
        network: hre.network.name,
        chainId: hre.network.config.chainId ?? null,
        contractName: "VerificationRegistry",
        address,
        abi: artifact.abi,
        deployedAt: new Date().toISOString(),
    };

    const outputPath = path.join(__dirname, "../deployed.json");
    fs.writeFileSync(outputPath, JSON.stringify(deployedData, null, 2));
    console.log(`📄 deployed.json saved to: ${outputPath}`);
    console.log(
        `🔗 View on Polygonscan Amoy: https://amoy.polygonscan.com/address/${address}`
    );
}

main().catch((err) => {
    console.error(err);
    process.exit(1);
});
