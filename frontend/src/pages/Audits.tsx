import { useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Filter } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";

type RiskLevel = "Low" | "Medium" | "High" | "Critical";

interface AuditEntry {
  id: string;
  projectName: string;
  trustScore: number;
  risk: RiskLevel;
  timestamp: string;
  txHash: string;
}

const audits: AuditEntry[] = [
  { id: "POC-001", projectName: "Amazon Reforestation Initiative", trustScore: 92, risk: "Low", timestamp: "2026-02-20 14:32", txHash: "0x8a3f...c2d1" },
  { id: "POC-002", projectName: "Sahel Agroforestry Program", trustScore: 82, risk: "Medium", timestamp: "2026-02-19 09:15", txHash: "0x1b7e...a4f8" },
  { id: "POC-003", projectName: "Southeast Asia Mangrove Restoration", trustScore: 45, risk: "High", timestamp: "2026-02-18 17:48", txHash: "0x9c2d...e7b3" },
  { id: "POC-004", projectName: "European Wind Farm Offset", trustScore: 28, risk: "Critical", timestamp: "2026-02-17 11:22", txHash: "0x4f1a...b8d6" },
  { id: "POC-005", projectName: "Central Africa REDD+ Project", trustScore: 88, risk: "Low", timestamp: "2026-02-16 08:05", txHash: "0x6e3c...d9a2" },
  { id: "POC-006", projectName: "India Solar Cookstove Program", trustScore: 71, risk: "Medium", timestamp: "2026-02-15 13:41", txHash: "0x2a8f...c1e5" },
];

const riskColors: Record<RiskLevel, string> = {
  Low: "text-trust-green-glow bg-primary/15",
  Medium: "text-highlight-orange bg-accent/15",
  High: "text-risk-red bg-destructive/15",
  Critical: "text-risk-red bg-destructive/20",
};

const riskOptions: ("All" | RiskLevel)[] = ["All", "Low", "Medium", "High", "Critical"];

const Audits = () => {
  const [filter, setFilter] = useState<"All" | RiskLevel>("All");
  const filtered = filter === "All" ? audits : audits.filter((a) => a.risk === filter);

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-6 pt-28 pb-20">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold md:text-4xl">
            Audit <span className="text-gradient-green">Logs</span>
          </h1>
          <p className="mt-3 text-muted-foreground">Historical verification records anchored on-chain.</p>

          {/* Filters */}
          <div className="mt-8 flex items-center gap-2 flex-wrap">
            <Filter className="h-4 w-4 text-muted-foreground" />
            {riskOptions.map((opt) => (
              <button
                key={opt}
                onClick={() => setFilter(opt)}
                className={`rounded-full px-4 py-1.5 text-xs font-medium transition-all ${
                  filter === opt
                    ? "bg-accent text-accent-foreground"
                    : "bg-secondary text-muted-foreground hover:text-foreground"
                }`}
              >
                {opt}
              </button>
            ))}
          </div>

          {/* Table */}
          <div className="mt-8 overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-secondary/30">
                  <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Project ID</th>
                  <th className="px-5 py-3.5 text-left font-medium text-muted-foreground hidden sm:table-cell">Project</th>
                  <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Score</th>
                  <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Risk</th>
                  <th className="px-5 py-3.5 text-left font-medium text-muted-foreground hidden md:table-cell">Timestamp</th>
                  <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Tx</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a, i) => (
                  <motion.tr
                    key={a.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="border-b border-border last:border-0 hover:bg-secondary/20 transition-colors"
                  >
                    <td className="px-5 py-4 font-mono text-xs">{a.id}</td>
                    <td className="px-5 py-4 hidden sm:table-cell">{a.projectName}</td>
                    <td className="px-5 py-4 font-bold">{a.trustScore}</td>
                    <td className="px-5 py-4">
                      <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${riskColors[a.risk]}`}>
                        {a.risk}
                      </span>
                    </td>
                    <td className="px-5 py-4 text-muted-foreground hidden md:table-cell">{a.timestamp}</td>
                    <td className="px-5 py-4">
                      <a href="https://amoy.polygonscan.com" target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-accent hover:underline text-xs">
                        {a.txHash} <ExternalLink className="h-3 w-3" />
                      </a>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      </div>
      <Footer />
    </main>
  );
};

export default Audits;
