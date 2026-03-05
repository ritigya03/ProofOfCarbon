/**
 * src/lib/blockchain.ts — Read-only viem client for VerificationRegistry.
 *
 * Uses the Polygon Amoy public RPC to query on-chain records directly from
 * the browser (no wallet required — all calls are read-only).
 */

import { createPublicClient, http, type Abi } from "viem";
import { polygonAmoy } from "viem/chains";

// ── Contract config ─────────────────────────────────────────────────────────

export const CONTRACT_ADDRESS = "0xcA46d6eecA22e04E1ae6fE6142ca9Cb3FBC10de0";
export const CHAIN_ID = 80002;
export const EXPLORER_BASE = "https://amoy.polygonscan.com";

export const VERIFICATION_REGISTRY_ABI: Abi = [
    {
        inputs: [{ internalType: "uint256", name: "id", type: "uint256" }],
        name: "getRecord",
        outputs: [
            {
                components: [
                    { internalType: "uint256", name: "id", type: "uint256" },
                    { internalType: "string", name: "projectName", type: "string" },
                    { internalType: "string", name: "companyName", type: "string" },
                    { internalType: "uint8", name: "trustScore", type: "uint8" },
                    { internalType: "uint8", name: "riskLevel", type: "uint8" },
                    { internalType: "string", name: "ipfsHash", type: "string" },
                    { internalType: "address", name: "verifier", type: "address" },
                    { internalType: "uint256", name: "timestamp", type: "uint256" },
                ],
                internalType: "struct VerificationRegistry.VerificationRecord",
                name: "",
                type: "tuple",
            },
        ],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [
            { internalType: "uint256", name: "offset", type: "uint256" },
            { internalType: "uint256", name: "limit", type: "uint256" },
        ],
        name: "getRecords",
        outputs: [
            {
                components: [
                    { internalType: "uint256", name: "id", type: "uint256" },
                    { internalType: "string", name: "projectName", type: "string" },
                    { internalType: "string", name: "companyName", type: "string" },
                    { internalType: "uint8", name: "trustScore", type: "uint8" },
                    { internalType: "uint8", name: "riskLevel", type: "uint8" },
                    { internalType: "string", name: "ipfsHash", type: "string" },
                    { internalType: "address", name: "verifier", type: "address" },
                    { internalType: "uint256", name: "timestamp", type: "uint256" },
                ],
                internalType: "struct VerificationRegistry.VerificationRecord[]",
                name: "page",
                type: "tuple[]",
            },
        ],
        stateMutability: "view",
        type: "function",
    },
    {
        inputs: [],
        name: "totalRecords",
        outputs: [{ internalType: "uint256", name: "", type: "uint256" }],
        stateMutability: "view",
        type: "function",
    },
] as const;

// ── Viem public client ──────────────────────────────────────────────────────

export const publicClient = createPublicClient({
    chain: polygonAmoy,
    transport: http("https://rpc-amoy.polygon.technology"),
});

// ── Helper types ────────────────────────────────────────────────────────────

export interface OnChainRecord {
    id: number;
    projectName: string;
    companyName: string;
    trustScore: number;
    riskLevel: number;
    ipfsHash: string;
    verifier: string;
    timestamp: number;
}

const RISK_LABELS = ["Low", "Medium", "High", "Critical"] as const;
export const riskLabel = (level: number) => RISK_LABELS[level] ?? "Unknown";

// ── Read helpers ────────────────────────────────────────────────────────────

export async function getTotalRecords(): Promise<number> {
    const result = await publicClient.readContract({
        address: CONTRACT_ADDRESS,
        abi: VERIFICATION_REGISTRY_ABI,
        functionName: "totalRecords",
    });
    return Number(result);
}

export async function getRecords(
    offset = 0,
    limit = 50
): Promise<OnChainRecord[]> {
    const result = await publicClient.readContract({
        address: CONTRACT_ADDRESS,
        abi: VERIFICATION_REGISTRY_ABI,
        functionName: "getRecords",
        args: [BigInt(offset), BigInt(limit)],
    });

    return (result as unknown[]).map((r: unknown) => {
        const rec = r as [bigint, string, string, number, number, string, string, bigint];
        return {
            id: Number(rec[0]),
            projectName: rec[1],
            companyName: rec[2],
            trustScore: rec[3],
            riskLevel: rec[4],
            ipfsHash: rec[5],
            verifier: rec[6],
            timestamp: Number(rec[7]),
        };
    });
}

export async function getRecord(id: number): Promise<OnChainRecord> {
    const result = await publicClient.readContract({
        address: CONTRACT_ADDRESS,
        abi: VERIFICATION_REGISTRY_ABI,
        functionName: "getRecord",
        args: [BigInt(id)],
    });

    const rec = result as unknown as [bigint, string, string, number, number, string, string, bigint];
    return {
        id: Number(rec[0]),
        projectName: rec[1],
        companyName: rec[2],
        trustScore: rec[3],
        riskLevel: rec[4],
        ipfsHash: rec[5],
        verifier: rec[6],
        timestamp: Number(rec[7]),
    };
}
