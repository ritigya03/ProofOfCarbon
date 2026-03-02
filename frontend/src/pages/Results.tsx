import { motion } from "framer-motion";
import { ExternalLink, ShieldCheck, AlertTriangle, Brain, Satellite, BarChart3, SearchCheck, MapPin, TreePine } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { useState } from "react";
import { useLocation, Link } from "react-router-dom";

// ── Static mock agent outputs (until baseline/fraud agents are built) ──
const mockAgentOutputs = [
  { icon: Brain,       name: "Project Analysis Agent",   summary: "",  score: null },
  { icon: Satellite,   name: "Satellite Evidence Agent",  summary: "",  score: null },
  { icon: BarChart3,   name: "Baseline Agent",            summary: "Baseline analysis pending — BaselineAgent not yet implemented.",   score: null },
  { icon: SearchCheck, name: "Fraud Reasoning Agent",     summary: "Registry cross-check pending — RegistryFraudAgent not yet implemented.", score: null },
];

const riskColor = (level: string) => {
  if (level === "LOW")      return "text-trust-green-glow";
  if (level === "MEDIUM")   return "text-highlight-orange";
  if (level === "HIGH")     return "text-orange-500";
  if (level === "CRITICAL") return "text-red-400";
  return "text-muted-foreground";
};

const TrustGauge = ({ score }: { score: number }) => {
  const radius = 80;
  const circumference = Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width="200" height="120" viewBox="0 0 200 120">
        <path d="M 20 100 A 80 80 0 0 1 180 100" fill="none" stroke="hsl(220, 12%, 16%)" strokeWidth="12" strokeLinecap="round" />
        <motion.path
          d="M 20 100 A 80 80 0 0 1 180 100"
          fill="none"
          stroke="url(#gaugeGradient)"
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1.5, ease: "easeOut" }}
        />
        <defs>
          <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="hsl(18, 82%, 34%)" />
            <stop offset="50%" stopColor="hsl(18, 90%, 59%)" />
            <stop offset="100%" stopColor="hsl(116, 50%, 35%)" />
          </linearGradient>
        </defs>
      </svg>
      <div className="absolute bottom-0 text-center">
        <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.8 }} className="text-4xl font-bold">
          {score}
        </motion.span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>
    </div>
  );
};

const Results = () => {
  const location = useLocation();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const apiResult: Record<string, any> | undefined = location.state?.result;

  const trustScore  = apiResult ? Math.round(apiResult.trust_score ?? 0) : 82;
  const riskLevel   = apiResult?.risk_level ?? "MEDIUM";
  const summary     = apiResult?.summary ?? "";
  const allFlags    = apiResult?.all_flags ?? [];
  const claimedHa   = apiResult?.claimed_hectares;
  const verifiedHa  = apiResult?.verified_hectares;
  const overlapPct  = apiResult?.overlap_percent;
  const paOverlapHa = apiResult?.protected_area_overlap_ha;
  const projectName = apiResult?.project_name ?? "Unknown Project";
  const state       = apiResult?.state ?? "";
  const forestType  = apiResult?.forest_type ?? "";

  // ── Satellite fields ────────────────────────────────────────────────────────
  const ndviCurrent    = apiResult?.ndvi_current_mean;
  const ndviHistoric   = apiResult?.ndvi_historical_mean;
  const ndviTrend      = apiResult?.ndvi_trend;           // INCREASING | STABLE | DECREASING
  const ndviAnomalyPct = apiResult?.ndvi_anomaly_score;
  const vegClass       = apiResult?.vegetation_class;
  const satRiskLevel   = apiResult?.satellite_risk_level;
  const satModifier    = apiResult?.satellite_trust_modifier;
  const satSummary     = apiResult?.satellite_summary;
  const satFlags       = apiResult?.satellite_flags ?? [];
  const ndviDataSource = apiResult?.ndvi_data_source;   // MODIS_MOD13Q1 | MOCK
  const hasSatData     = ndviCurrent != null;

  const agentOutputs = mockAgentOutputs.map((a, i) => {
    if (i === 0 && apiResult) {
      return { ...a, summary: summary || "Geospatial analysis complete.", score: trustScore };
    }
    if (i === 1 && hasSatData) {
      const trendText = ndviTrend === "DECREASING" ? " — declining trend detected" :
                        ndviTrend === "INCREASING" ? " — vegetation growing" : "";
      return {
        ...a,
        summary: satSummary || `NDVI ${ndviCurrent?.toFixed(4)} · ${vegClass?.replace(/_/g, " ")}${trendText}`,
        score: satModifier != null ? Math.max(0, Math.min(100, 50 + satModifier * 2)) : null,
      };
    }
    return a;
  });

  const [expandedAgent, setExpandedAgent] = useState<number | null>(null);

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-6 pt-28 pb-20">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mx-auto max-w-4xl">
          <h1 className="text-3xl font-bold md:text-4xl">
            Verification <span className="text-gradient-green">Results</span>
          </h1>

          {(projectName !== "Unknown Project" || state) && (
            <div className="mt-3 flex flex-wrap gap-3 text-sm text-muted-foreground">
              {projectName !== "Unknown Project" && (
                <span className="inline-flex items-center gap-1.5"><TreePine className="h-4 w-4" /> {projectName}</span>
              )}
              {state && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-4 w-4" /> {state}{forestType && ` · ${forestType}`}
                </span>
              )}
            </div>
          )}

          {/* Score + Risk */}
          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <div className="rounded-xl border border-border bg-gradient-card p-8 text-center">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider mb-4">Trust Score</h3>
              <TrustGauge score={trustScore} />
            </div>
            <div className="rounded-xl border border-border bg-gradient-card p-8 flex flex-col items-center justify-center gap-3">
              <h3 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Risk Level</h3>
              <span className={`inline-flex items-center gap-2 rounded-full bg-accent/15 px-5 py-2 text-lg font-bold ${riskColor(riskLevel)}`}>
                <AlertTriangle className="h-5 w-5" />
                {riskLevel}
              </span>
              <p className="text-xs text-muted-foreground">Based on multi-agent consensus</p>
            </div>
          </div>

          {/* Spatial Metrics */}
          {apiResult && (
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: "Claimed Area",         value: claimedHa   != null ? `${claimedHa.toFixed(1)} ha`  : "—" },
                { label: "Verified Area",        value: verifiedHa  != null ? `${verifiedHa.toFixed(1)} ha`  : "—" },
                { label: "Overlap",              value: overlapPct  != null ? `${overlapPct.toFixed(1)}%`    : "—" },
                { label: "PA Overlap",           value: paOverlapHa != null ? `${paOverlapHa.toFixed(1)} ha` : "—" },
              ].map((m) => (
                <div key={m.label} className="rounded-xl border border-border bg-gradient-card px-4 py-5 text-center">
                  <p className="text-xs text-muted-foreground mb-1">{m.label}</p>
                  <p className="text-lg font-bold">{m.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* Satellite NDVI Card */}
          {hasSatData && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="mt-6 rounded-xl border border-border bg-gradient-card p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <Satellite className="h-5 w-5 text-trust-green-glow" />
                  <h3 className="font-semibold text-sm">Satellite Evidence — NASA MODIS NDVI</h3>
                </div>
                <div className="flex items-center gap-2">
                  {ndviDataSource && (
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      ndviDataSource === "MODIS_MOD13Q1"
                        ? "border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10"
                        : "border-yellow-500/40 text-yellow-400 bg-yellow-500/10"
                    }`}>
                      {ndviDataSource === "MODIS_MOD13Q1" ? "Live · MODIS/061" : "Mock Data"}
                    </span>
                  )}
                  {satRiskLevel && (
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      satRiskLevel === "LOW" ? "border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10" :
                      satRiskLevel === "MEDIUM" ? "border-yellow-500/40 text-yellow-400 bg-yellow-500/10" :
                      "border-red-500/40 text-red-400 bg-red-500/10"
                    }`}>
                      {satRiskLevel}
                    </span>
                  )}
                </div>
              </div>

              {/* NDVI Bars */}
              <div className="space-y-4">
                {/* Current */}
                <div>
                  <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                    <span>Current NDVI <span className="text-foreground/40">(last 3 yr avg)</span></span>
                    <span className="font-mono font-semibold text-foreground">{ndviCurrent?.toFixed(4)}</span>
                  </div>
                  <div className="h-3 w-full rounded-full bg-secondary/60 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(ndviCurrent ?? 0) * 100}%` }}
                      transition={{ duration: 1.2, ease: "easeOut" }}
                      className={`h-full rounded-full ${
                        (ndviCurrent ?? 0) >= 0.6 ? "bg-trust-green-glow" :
                        (ndviCurrent ?? 0) >= 0.4 ? "bg-yellow-400" :
                        (ndviCurrent ?? 0) >= 0.2 ? "bg-orange-400" : "bg-red-500"
                      }`}
                    />
                  </div>
                </div>

                {/* Historical */}
                {ndviHistoric != null && (
                  <div>
                    <div className="flex justify-between text-xs text-muted-foreground mb-1.5">
                      <span>Historic NDVI <span className="text-foreground/40">(3–6 yr ago)</span></span>
                      <span className="font-mono font-semibold text-foreground">{ndviHistoric.toFixed(4)}</span>
                    </div>
                    <div className="h-3 w-full rounded-full bg-secondary/60 overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${ndviHistoric * 100}%` }}
                        transition={{ duration: 1.2, ease: "easeOut", delay: 0.15 }}
                        className="h-full rounded-full bg-muted-foreground/40"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Stats row */}
              <div className="mt-5 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg bg-secondary/40 px-3 py-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Trend</p>
                  <p className={`text-sm font-bold ${
                    ndviTrend === "DECREASING" ? "text-red-400" :
                    ndviTrend === "INCREASING" ? "text-trust-green-glow" : "text-muted-foreground"
                  }`}>
                    {ndviTrend === "INCREASING" ? "▲ " : ndviTrend === "DECREASING" ? "▼ " : "→ "}
                    {ndviTrend ?? "—"}
                  </p>
                </div>
                <div className="rounded-lg bg-secondary/40 px-3 py-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Change</p>
                  <p className={`text-sm font-bold ${
                    (ndviAnomalyPct ?? 0) < -10 ? "text-red-400" :
                    (ndviAnomalyPct ?? 0) > 10  ? "text-trust-green-glow" : "text-muted-foreground"
                  }`}>
                    {ndviAnomalyPct != null ? `${ndviAnomalyPct > 0 ? "+" : ""}${ndviAnomalyPct.toFixed(1)}%` : "—"}
                  </p>
                </div>
                <div className="rounded-lg bg-secondary/40 px-3 py-3">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Trust Adj.</p>
                  <p className={`text-sm font-bold ${
                    (satModifier ?? 0) < 0 ? "text-red-400" :
                    (satModifier ?? 0) > 0 ? "text-trust-green-glow" : "text-muted-foreground"
                  }`}>
                    {satModifier != null ? `${satModifier > 0 ? "+" : ""}${satModifier}` : "—"}
                  </p>
                </div>
              </div>

              {/* Vegetation class + summary */}
              {(vegClass || satSummary) && (
                <div className="mt-4 space-y-2">
                  {vegClass && (
                    <p className="text-xs text-muted-foreground">
                      Vegetation class: <span className="font-semibold text-foreground">{vegClass.replace(/_/g, " ")}</span>
                    </p>
                  )}
                  {satSummary && (
                    <p className="text-xs text-muted-foreground leading-relaxed border-t border-border pt-3 mt-3">
                      {satSummary}
                    </p>
                  )}
                </div>
              )}

              {/* Satellite flags */}
              {satFlags.length > 0 && (
                <ul className="mt-4 space-y-1 border-t border-border pt-3">
                  {satFlags.map((f: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className={`mt-0.5 shrink-0 ${f.startsWith("CRITICAL") || f.startsWith("!!") ? "text-red-400" : f.startsWith("WARNING") ? "text-yellow-400" : "text-trust-green-glow"}`}>•</span>
                      {f}
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          )}

          {/* Flags */}

          {allFlags.length > 0 && (
            <div className="mt-6 rounded-xl border border-red-500/20 bg-red-500/5 px-5 py-4">
              <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-3">Flags</p>
              <ul className="space-y-1.5">
                {allFlags.map((flag: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span className="mt-0.5 text-red-400 shrink-0">•</span> {flag}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Agent Reports */}
          <div className="mt-10 space-y-3">
            <h3 className="text-lg font-semibold mb-4">Agent Reports</h3>
            {agentOutputs.map((agent, i) => (
              <motion.div key={agent.name} initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
                <button
                  onClick={() => setExpandedAgent(expandedAgent === i ? null : i)}
                  className="w-full rounded-xl border border-border bg-gradient-card p-5 text-left transition-all hover:border-glow-green"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <agent.icon className="h-5 w-5 text-trust-green-glow" />
                      <span className="font-medium text-sm">{agent.name}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      {agent.score != null ? (
                        <span className="text-sm font-bold text-trust-green-glow">{agent.score}/100</span>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Pending</span>
                      )}
                      <span className="text-muted-foreground text-xs">{expandedAgent === i ? "▲" : "▼"}</span>
                    </div>
                  </div>
                  {expandedAgent === i && (
                    <motion.p
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="mt-4 text-sm text-muted-foreground leading-relaxed border-t border-border pt-4"
                    >
                      {agent.summary}
                    </motion.p>
                  )}
                </button>
              </motion.div>
            ))}
          </div>

          {/* Blockchain Proof */}
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}
            className="mt-10 rounded-xl border border-border bg-gradient-card p-8"
          >
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="h-6 w-6 text-trust-green-glow" />
              <h3 className="text-lg font-semibold">Blockchain Proof</h3>
              <span className="ml-auto text-xs text-muted-foreground italic">Smart contract anchoring — coming soon</span>
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Transaction Hash</span>
                <code className="font-mono text-xs text-foreground bg-secondary/50 px-3 py-1.5 rounded break-all">0x7f3a8b...e4d2c1a9f6b8</code>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Network</span>
                <span className="text-foreground">Polygon Amoy Testnet</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Status</span>
                <span className="text-xs text-muted-foreground italic">Pending blockchain integration</span>
              </div>
            </div>
            <a href="https://amoy.polygonscan.com" target="_blank" rel="noopener noreferrer"
              className="mt-5 inline-flex items-center gap-2 text-sm text-accent hover:underline">
              View on Explorer <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </motion.div>

          <div className="mt-8 flex justify-end">
            <Link to="/verify" className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary/50 px-5 py-2.5 text-sm font-medium transition-all hover:bg-secondary">
              ← Verify Another Project
            </Link>
          </div>

        </motion.div>
      </div>
      <Footer />
    </main>
  );
};

export default Results;
