/**
 * ignition/modules/VerificationRegistry.ts
 * Hardhat Ignition module for deploying VerificationRegistry.
 *
 * Deploy command:
 *   npx hardhat ignition deploy ignition/modules/VerificationRegistry.ts --network amoy
 *
 * After deploying, run:
 *   node scripts/save-deployed.mjs
 * to generate deployed.json from the Ignition deployment artifacts.
 */

import { buildModule } from "@nomicfoundation/hardhat-ignition/modules";

const VerificationRegistryModule = buildModule(
    "VerificationRegistryModule",
    (m) => {
        const registry = m.contract("VerificationRegistry");
        return { registry };
    }
);

export default VerificationRegistryModule;
