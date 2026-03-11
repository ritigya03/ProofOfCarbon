import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, Filter, Loader2, AlertCircle } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { EXPLORER_BASE } from "@/lib/blockchain";

type RiskLevel = "Low" | "Medium" | "High" | "Critical";

interface AuditEntry {
  id: number;
  projectName: string;
  companyName: string;
  trustScore: number;
  risk: RiskLevel;
  timestamp: string;
  verifier: string;
}

const RISK_LABELS: Record<number, RiskLevel> = {
  0: "Low",
  1: "Medium",
  2: "High",
  3: "Critical",
};

const riskColors: Record<RiskLevel, string> = {
  Low: "text-trust-green-glow bg-primary/15",
  Medium: "text-highlight-orange bg-accent/15",
  High: "text-risk-red bg-destructive/15",
  Critical: "text-risk-red bg-destructive/20",
};

const riskOptions: ("All" | RiskLevel)[] = ["All", "Low", "Medium", "High", "Critical"];

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

const Audits = () => {
  const [filter, setFilter] = useState<"All" | RiskLevel>("All");
  const [audits, setAudits] = useState<AuditEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAudits = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_BASE}/audits?offset=0&limit=100`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const entries: AuditEntry[] = (data.records ?? []).map(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (r: any) => ({
            id: r.id,
            projectName: r.project_name || "Unknown Project",
            companyName: r.company_name || "Unknown",
            trustScore: r.trust_score,
            risk: RISK_LABELS[typeof r.risk_level === "number" ? r.risk_level : 1] ?? "Medium",
            timestamp: r.timestamp
              ? new Date(r.timestamp * 1000).toLocaleString()
              : "—",
            verifier: r.verifier ?? "—",
          })
        );

        setAudits(entries);
      } catch (e) {
        console.error("Failed to fetch audits:", e);
        setError(e instanceof Error ? e.message : "Failed to load audit records");
      } finally {
        setLoading(false);
      }
    };

    fetchAudits();
  }, []);

  const filtered = filter === "All" ? audits : audits.filter((a) => a.risk === filter);

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-6 pt-28 pb-20">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-3xl font-bold md:text-4xl">
            Audit <span className="text-gradient-green">Logs</span>
          </h1>
          <p className="mt-3 text-muted-foreground">
            Verification records anchored on-chain via VerificationRegistry on Polygon Amoy.
          </p>

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

          {/* Loading / Error / Empty states */}
          {loading && (
            <div className="mt-16 flex flex-col items-center gap-3 text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin" />
              <p className="text-sm">Loading on-chain records…</p>
            </div>
          )}

          {error && (
            <div className="mt-8 flex items-center gap-3 rounded-xl border border-red-500/30 bg-red-500/10 px-5 py-4 text-sm text-red-400">
              <AlertCircle className="h-5 w-5 shrink-0" />
              <p>{error}</p>
            </div>
          )}

          {!loading && !error && audits.length === 0 && (
            <div className="mt-16 text-center text-muted-foreground">
              <p className="text-sm">No verification records found on-chain yet.</p>
              <p className="text-xs mt-1">
                Records will appear here after a project verification is submitted with blockchain enabled.
              </p>
            </div>
          )}

          {/* Table */}
          {!loading && filtered.length > 0 && (
            <div className="mt-8 overflow-x-auto rounded-xl border border-border">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-secondary/30">
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">ID</th>
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground hidden sm:table-cell">Project</th>
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground hidden md:table-cell">Company</th>
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Score</th>
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Risk</th>
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground hidden md:table-cell">Timestamp</th>
                    <th className="px-5 py-3.5 text-left font-medium text-muted-foreground">Verifier</th>
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
                      <td className="px-5 py-4 font-mono text-xs">#{a.id}</td>
                      <td className="px-5 py-4 hidden sm:table-cell">{a.projectName}</td>
                      <td className="px-5 py-4 hidden md:table-cell text-muted-foreground">{a.companyName}</td>
                      <td className="px-5 py-4 font-bold">{a.trustScore}</td>
                      <td className="px-5 py-4">
                        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-medium ${riskColors[a.risk]}`}>
                          {a.risk}
                        </span>
                      </td>
                      <td className="px-5 py-4 text-muted-foreground hidden md:table-cell">{a.timestamp}</td>
                      <td className="px-5 py-4">
                        <a
                          href={`${EXPLORER_BASE}/address/${a.verifier}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-accent hover:underline text-xs font-mono"
                        >
                          {a.verifier.slice(0, 6)}…{a.verifier.slice(-4)}
                          <ExternalLink className="h-3 w-3" />
                        </a>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Footer info */}
          {!loading && audits.length > 0 && (
            <p className="mt-4 text-xs text-muted-foreground">
              Showing {filtered.length} of {audits.length} total on-chain records · 
              <a
                href={`${EXPLORER_BASE}/address/0xcA46d6eecA22e04E1ae6fE6142ca9Cb3FBC10de0`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-accent hover:underline ml-1"
              >
                View contract on Polygonscan
              </a>
            </p>
          )}
        </motion.div>
      </div>
      <Footer />
    </main>
  );
};

export default Audits;
