import hardhatToolboxViemPlugin from "@nomicfoundation/hardhat-toolbox-viem";
import { defineConfig } from "hardhat/config";
import fs from "fs";
import path from "path";

// ── Load .env manually (no dotenv package needed) ─────────────────────────────
const envPath = path.join(import.meta.dirname, ".env");
if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, "utf-8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const val = trimmed.slice(eqIdx + 1).trim();
    if (key && !(key in process.env)) {
      process.env[key] = val;
    }
  }
}

const amoyRpc = process.env.AMOY_RPC_URL ?? "https://rpc-amoy.polygon.technology";
const polygonRpc = process.env.POLYGON_RPC_URL ?? "https://polygon-rpc.com";
const deployerKey = process.env.DEPLOYER_PRIVATE_KEY ?? "";
const sepoliaRpc = process.env.SEPOLIA_RPC_URL ?? "";
const sepoliaKey = process.env.SEPOLIA_PRIVATE_KEY ?? "";

export default defineConfig({
  plugins: [hardhatToolboxViemPlugin],
  solidity: {
    profiles: {
      default: {
        version: "0.8.28",
      },
      production: {
        version: "0.8.28",
        settings: {
          optimizer: {
            enabled: true,
            runs: 200,
          },
        },
      },
    },
  },
  networks: {
    hardhatMainnet: {
      type: "edr-simulated",
      chainType: "l1",
    },
    hardhatOp: {
      type: "edr-simulated",
      chainType: "op",
    },
    // Polygon Amoy Testnet (chain ID: 80002)
    amoy: {
      type: "http",
      chainType: "l1",
      url: amoyRpc,
      accounts: deployerKey ? [deployerKey] : [],
      chainId: 80002,
    },
    // Polygon Mainnet (chain ID: 137) — for production use
    polygon: {
      type: "http",
      chainType: "l1",
      url: polygonRpc,
      accounts: deployerKey ? [deployerKey] : [],
      chainId: 137,
    },
    // Sepolia (kept for reference)
    ...(sepoliaRpc && sepoliaKey
      ? {
        sepolia: {
          type: "http" as const,
          chainType: "l1" as const,
          url: sepoliaRpc,
          accounts: [sepoliaKey],
        },
      }
      : {}),
  },
});
