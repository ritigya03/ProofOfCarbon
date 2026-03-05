import { motion } from "framer-motion";
import { ExternalLink, ShieldCheck, AlertTriangle, Brain, Satellite, SearchCheck, MapPin, TreePine, Map, BarChart3 } from "lucide-react";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { useState, Suspense, lazy } from "react";
import { useLocation, Link } from "react-router-dom";

// Lazy-load the map so Leaflet only initialises client-side
const SatelliteMap = lazy(() => import("@/components/SatelliteMap"));

// ── Helpers ───────────────────────────────────────────────────────────────────

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
        <motion.span
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8 }}
          className="text-4xl font-bold"
        >
          {score}
        </motion.span>
        <span className="text-sm text-muted-foreground">/100</span>
      </div>
    </div>
  );
};

// ── Main component ─────────────────────────────────────────────────────────────

const Results = () => {
  const location = useLocation();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const apiResult: Record<string, any> | undefined = location.state?.result;

  const [expandedAgent, setExpandedAgent] = useState<number | null>(null);

  // ── Stage 1: Spatial ──────────────────────────────────────────────────────
  const trustScore  = apiResult ? Math.round(apiResult.trust_score ?? 0) : 82;
  const riskLevel   = apiResult?.risk_level ?? "MEDIUM";
  const summary     = apiResult?.summary ?? "";
  const allFlags    = apiResult?.all_flags ?? [];
  const claimedHa   = apiResult?.claimed_hectares;
  const verifiedHa  = apiResult?.verified_hectares;
  const overlapPct  = apiResult?.overlap_percent;
  const paOverlapHa = apiResult?.protected_area_overlap_ha ?? 0;
  const projectName = apiResult?.project_name ?? "Unknown Project";
  const state       = apiResult?.state ?? "";
  const forestType  = apiResult?.forest_type ?? "";
  const bbox        = apiResult?.bbox as { min_lon: number; min_lat: number; max_lon: number; max_lat: number } | undefined;
  const areaMismatchPct = apiResult?.area_mismatch_pct as number | undefined;
  const textClaimedHa   = apiResult?.text_claimed_ha as number | undefined;

  // ── Stage 2: Satellite ────────────────────────────────────────────────────
  const ndviCurrent    = apiResult?.ndvi_current_mean;
  const ndviHistoric   = apiResult?.ndvi_historical_mean;
  const ndviTrend      = apiResult?.ndvi_trend;
  const ndviAnomalyPct = apiResult?.ndvi_anomaly_score;
  const vegClass       = apiResult?.vegetation_class;
  const satRiskLevel   = apiResult?.satellite_risk_level;
  const satModifier    = apiResult?.satellite_trust_modifier;
  const satSummary     = apiResult?.satellite_summary;
  const satFlags       = apiResult?.satellite_flags ?? [];
  const ndviDataSource = apiResult?.ndvi_data_source;
  const hasSatData     = ndviCurrent != null;

  // ── agentOutputs defined INSIDE component so all variables are in scope ───
  const agentOutputs = [
    {
      icon: Brain,
      name: "Project Analysis Agent",
      summary: summary || "Geospatial analysis complete.",
      score: apiResult ? Math.round((apiResult as any).spatial_trust_score ?? apiResult.trust_score ?? 0) : null,
      detail: apiResult ? [
        `Overlap: ${overlapPct?.toFixed(1)}%`,
        `Claimed: ${claimedHa?.toFixed(1)} ha / Verified: ${verifiedHa?.toFixed(1)} ha`,
        paOverlapHa > 0 ? `⚠ Protected area overlap: ${paOverlapHa?.toFixed(1)} ha` : null,
      ].filter(Boolean) as string[] : [],
    },
    {
      icon: Satellite,
      name: "Satellite Evidence Agent",
      summary: satSummary || (hasSatData
        ? `NDVI ${ndviCurrent?.toFixed(4)} · ${vegClass?.replace(/_/g, " ")}`
        : "Satellite data not available."),
      score: hasSatData && satModifier != null
        ? Math.max(0, Math.min(100, 50 + satModifier * 3))
        : null,
      detail: hasSatData ? [
        `Vegetation: ${vegClass?.replace(/_/g, " ")}`,
        `Trend: ${ndviTrend}`,
        `Trust modifier: ${(satModifier ?? 0) > 0 ? "+" : ""}${satModifier}`,
      ] : [],
    },
    {
      icon: BarChart3,
      name: "Historical Baseline Agent",
      summary: apiResult?.baseline_summary || "Baseline analysis complete.",
      score: apiResult?.additionality_score != null
        ? Math.round(apiResult.additionality_score)
        : null,
      detail: apiResult ? [
        `Verdict: ${apiResult.additionality_verdict}`,
        `Pressure: ${apiResult.deforestation_pressure}`,
        `Carbon at risk: ${((apiResult.carbon_at_risk_tonnes_co2e ?? 0) / 1000).toFixed(1)}k tCO₂e`,
      ] : [],
    },
    {
      icon: SearchCheck,
      name: "Fraud Detection Agent",
      summary: apiResult?.fraud_summary || "Fraud analysis not available.",
      score: apiResult?.anomaly_score != null
        ? Math.max(0, 100 - apiResult.anomaly_score)
        : null,
      detail: apiResult?.fraud_patterns
        ? Object.entries(apiResult.fraud_patterns)
            .filter(([, v]) => v !== "CLEAR")
            .map(([k, v]) => `${k.replace(/_/g, " ")}: ${v}`)
        : [],
    },
    {
      icon: ShieldCheck,
      name: "Verifier Agent",
      summary: apiResult?.verification_summary || "Final verification not available.",
      score: apiResult?.final_trust_score != null
        ? Math.round(apiResult.final_trust_score)
        : null,
      detail: [
        apiResult?.final_verdict
          ? `Verdict: ${apiResult.final_verdict.replace(/_/g, " ")}`
          : null,
        apiResult?.confidence ? `Confidence: ${apiResult.confidence}` : null,
        apiResult?.recommendation ?? null,
      ].filter(Boolean) as string[],
    },
  ];

  return (
    <main className="min-h-screen">
      <Navbar />
      <div className="container mx-auto px-6 pt-28 pb-20">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mx-auto max-w-4xl"
        >
          <h1 className="text-3xl font-bold md:text-4xl">
            Verification <span className="text-gradient-green">Results</span>
          </h1>

          {(projectName !== "Unknown Project" || state) && (
            <div className="mt-3 flex flex-wrap gap-3 text-sm text-muted-foreground">
              {projectName !== "Unknown Project" && (
                <span className="inline-flex items-center gap-1.5">
                  <TreePine className="h-4 w-4" /> {projectName}
                </span>
              )}
              {state && (
                <span className="inline-flex items-center gap-1.5">
                  <MapPin className="h-4 w-4" /> {state}{forestType && ` · ${forestType}`}
                </span>
              )}
            </div>
          )}

          {/* ── Trust Score + Risk Level ──────────────────────────────────── */}
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

          {/* ── Spatial Metrics ───────────────────────────────────────────── */}
          {apiResult && (
            <div className="mt-6 grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: "Claimed Area",  value: claimedHa   != null ? `${claimedHa.toFixed(1)} ha`   : "—" },
                { label: "Verified Area", value: verifiedHa  != null ? `${verifiedHa.toFixed(1)} ha`   : "—" },
                { label: "Overlap",       value: overlapPct  != null ? `${overlapPct.toFixed(1)}%`     : "—" },
                { label: "PA Overlap",    value: paOverlapHa != null ? `${paOverlapHa.toFixed(1)} ha`  : "—" },
              ].map((m) => (
                <div key={m.label} className="rounded-xl border border-border bg-gradient-card px-4 py-5 text-center">
                  <p className="text-xs text-muted-foreground mb-1">{m.label}</p>
                  <p className="text-lg font-bold">{m.value}</p>
                </div>
              ))}
            </div>
          )}

          {/* ── Satellite Map ─────────────────────────────────────────────── */}
          {bbox && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="mt-6 rounded-xl border border-border bg-gradient-card overflow-hidden"
            >
              <div className="flex items-center justify-between px-5 py-4 border-b border-border">
                <div className="flex items-center gap-3">
                  <Map className="h-5 w-5 text-trust-green-glow" />
                  <h3 className="font-semibold text-sm">Claimed Area — Satellite View</h3>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10">
                    Live · ESRI
                  </span>
                  {areaMismatchPct !== undefined && areaMismatchPct > 20 && (
                    <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                      areaMismatchPct > 200
                        ? "border-red-500/40 text-red-400 bg-red-500/10"
                        : areaMismatchPct > 50
                        ? "border-orange-500/40 text-orange-400 bg-orange-500/10"
                        : "border-yellow-500/40 text-yellow-400 bg-yellow-500/10"
                    }`}>
                      ⚠ Area mismatch {areaMismatchPct.toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>

              {/* Area mismatch explanation banner */}
              {areaMismatchPct !== undefined && areaMismatchPct > 20 && textClaimedHa !== undefined && (
                <div className={`px-5 py-3 text-xs border-b border-border ${
                  areaMismatchPct > 200
                    ? "bg-red-500/10 text-red-400"
                    : areaMismatchPct > 50
                    ? "bg-orange-500/10 text-orange-400"
                    : "bg-yellow-500/10 text-yellow-400"
                }`}>
                  <strong>Area discrepancy detected:</strong> Description claims{" "}
                  <strong>{textClaimedHa.toFixed(0)} ha</strong> but KMZ file measures{" "}
                  <strong>{claimedHa?.toFixed(1)} ha</strong>{" "}({areaMismatchPct.toFixed(0)}% difference)
                </div>
              )}

              <Suspense fallback={
                <div className="h-[400px] flex items-center justify-center text-sm text-muted-foreground">
                  Loading map…
                </div>
              }>
                <SatelliteMap bbox={bbox} areaHa={claimedHa} referenceGeojson={apiResult?.reference_geojson} />
              </Suspense>

              <div className="px-5 py-3 border-t border-border">
                <p className="text-[10px] text-muted-foreground">
                  <span className="text-sky-400">▭</span> Blue dashed = claimed KMZ boundary · <span className="text-green-500">■</span> Forest · <span className="text-cyan-400">■</span> Plantation · <span className="text-lime-400">■</span> Scrub · Imagery © Esri, USDA, USGS
                </p>
              </div>
            </motion.div>
          )}

          {/* ── Stage 2: Satellite NDVI Card ──────────────────────────────── */}
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
                      satRiskLevel === "LOW"    ? "border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10" :
                      satRiskLevel === "MEDIUM" ? "border-yellow-500/40 text-yellow-400 bg-yellow-500/10" :
                                                  "border-red-500/40 text-red-400 bg-red-500/10"
                    }`}>
                      {satRiskLevel}
                    </span>
                  )}
                </div>
              </div>

              <div className="space-y-4">
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
                    {ndviAnomalyPct != null
                      ? `${ndviAnomalyPct > 0 ? "+" : ""}${ndviAnomalyPct.toFixed(1)}%`
                      : "—"}
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

              {satFlags.length > 0 && (
                <ul className="mt-4 space-y-1 border-t border-border pt-3">
                  {satFlags.map((f: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className={`mt-0.5 shrink-0 ${
                        f.startsWith("CRITICAL") || f.startsWith("!!")
                          ? "text-red-400"
                          : f.startsWith("WARNING")
                          ? "text-yellow-400"
                          : "text-trust-green-glow"
                      }`}>•</span>
                      {f}
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          )}

          {/* ── Stage 2.5: Baseline & Additionality ──────────────────────── */}
          {apiResult?.additionality_verdict && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28 }}
              className="mt-6 rounded-xl border border-border bg-gradient-card p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <TreePine className="h-5 w-5 text-trust-green-glow" />
                  <h3 className="font-semibold text-sm">Baseline & Additionality</h3>
                </div>
                <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                  apiResult.additionality_verdict === "STRONG"
                    ? "border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10"
                    : apiResult.additionality_verdict === "MODERATE"
                    ? "border-yellow-500/40 text-yellow-400 bg-yellow-500/10"
                    : apiResult.additionality_verdict === "WEAK"
                    ? "border-orange-500/40 text-orange-400 bg-orange-500/10"
                    : "border-red-500/40 text-red-400 bg-red-500/10"
                }`}>
                  {apiResult.additionality_verdict} Additionality
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
                {[
                  {
                    label: "Deforestation Pressure",
                    value: apiResult.deforestation_pressure ?? "—",
                    color: apiResult.deforestation_pressure === "CRITICAL" ? "text-red-400"
                         : apiResult.deforestation_pressure === "HIGH"     ? "text-orange-400"
                         : apiResult.deforestation_pressure === "MEDIUM"   ? "text-yellow-400"
                         : "text-trust-green-glow",
                  },
                  {
                    label: "Additionality Score",
                    value: apiResult.additionality_score != null ? `${apiResult.additionality_score.toFixed(1)}/100` : "—",
                    color: "text-foreground",
                  },
                  {
                    label: "Counterfactual Loss",
                    value: apiResult.counterfactual_loss_ha != null ? `${apiResult.counterfactual_loss_ha.toFixed(1)} ha` : "—",
                    color: "text-foreground",
                  },
                  {
                    label: "Carbon at Risk",
                    value: apiResult.carbon_at_risk_tonnes_co2e != null
                      ? `${(apiResult.carbon_at_risk_tonnes_co2e / 1000).toFixed(1)}k tCO₂e`
                      : "—",
                    color: "text-foreground",
                  },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg bg-secondary/40 px-3 py-3 text-center">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">{m.label}</p>
                    <p className={`text-sm font-bold ${m.color}`}>{m.value}</p>
                  </div>
                ))}
              </div>

              {apiResult.counterfactual_assessment && (
                <div className="space-y-2 border-t border-border pt-4">
                  <div>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Counterfactual Scenario</p>
                    <p className="text-xs text-muted-foreground leading-relaxed">{apiResult.counterfactual_assessment}</p>
                  </div>
                  {apiResult.permanence_assessment && (
                    <div>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1 mt-3">Permanence Assessment</p>
                      <p className="text-xs text-muted-foreground leading-relaxed">{apiResult.permanence_assessment}</p>
                    </div>
                  )}
                  {apiResult.baseline_summary && (
                    <p className="text-xs text-muted-foreground leading-relaxed border-t border-border pt-3 mt-3">
                      {apiResult.baseline_summary}
                    </p>
                  )}
                </div>
              )}
            </motion.div>
          )}

          {/* ── Stage 4: Final Verdict ────────────────────────────────────── */}
          {apiResult?.final_verdict && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="mt-6 rounded-xl border border-border bg-gradient-card p-6"
            >
              <div className="flex items-center gap-3 mb-5">
                <ShieldCheck className="h-5 w-5 text-trust-green-glow" />
                <h3 className="font-semibold text-sm">Final Verdict</h3>
                <span className={`ml-auto text-xs font-bold uppercase tracking-wider px-3 py-1 rounded-full border ${
                  apiResult.final_verdict === "VERIFIED"
                    ? "border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10"
                    : apiResult.final_verdict === "CONDITIONALLY_VERIFIED"
                    ? "border-yellow-500/40 text-yellow-400 bg-yellow-500/10"
                    : apiResult.final_verdict === "REQUIRES_REVIEW"
                    ? "border-orange-500/40 text-orange-400 bg-orange-500/10"
                    : "border-red-500/40 text-red-400 bg-red-500/10"
                }`}>
                  {apiResult.final_verdict.replace(/_/g, " ")}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-5">
                <div className="rounded-lg bg-secondary/40 px-4 py-3 text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Final Trust Score</p>
                  <p className="text-xl font-bold">
                    {Math.round(apiResult.final_trust_score ?? 0)}
                    <span className="text-xs text-muted-foreground">/100</span>
                  </p>
                </div>
                <div className="rounded-lg bg-secondary/40 px-4 py-3 text-center">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Confidence</p>
                  <p className={`text-sm font-bold ${
                    apiResult.confidence === "HIGH"   ? "text-trust-green-glow" :
                    apiResult.confidence === "MEDIUM" ? "text-yellow-400" : "text-muted-foreground"
                  }`}>{apiResult.confidence ?? "—"}</p>
                </div>
              </div>

              {apiResult.recommendation && (
                <div className="rounded-lg border border-border bg-secondary/20 px-4 py-3 mb-4">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-1">Recommendation</p>
                  <p className="text-sm text-foreground">{apiResult.recommendation}</p>
                </div>
              )}

              {apiResult.key_findings?.length > 0 && (
                <div>
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wider mb-2">Key Findings</p>
                  <ul className="space-y-1.5">
                    {apiResult.key_findings.map((f: string, i: number) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                        <span className="mt-0.5 text-trust-green-glow shrink-0">•</span> {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {apiResult.verification_summary && (
                <p className="mt-4 text-xs text-muted-foreground leading-relaxed border-t border-border pt-3">
                  {apiResult.verification_summary}
                </p>
              )}
            </motion.div>
          )}

          {/* ── Stage 3: Fraud Detection ──────────────────────────────────── */}
          {apiResult?.fraud_patterns && (
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.25 }}
              className="mt-6 rounded-xl border border-border bg-gradient-card p-6"
            >
              <div className="flex items-center justify-between mb-5">
                <div className="flex items-center gap-3">
                  <SearchCheck className="h-5 w-5 text-trust-green-glow" />
                  <h3 className="font-semibold text-sm">Fraud Detection</h3>
                  {apiResult.ml_confidence != null && (
                    <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border border-purple-500/40 text-purple-400 bg-purple-500/10">
                      ML · {(apiResult.ml_confidence * 100).toFixed(0)}% conf
                    </span>
                  )}
                </div>
                {apiResult.anomaly_score != null && (
                  <span className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                    apiResult.anomaly_score > 60
                      ? "border-red-500/40 text-red-400 bg-red-500/10"
                      : apiResult.anomaly_score > 30
                      ? "border-yellow-500/40 text-yellow-400 bg-yellow-500/10"
                      : "border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10"
                  }`}>
                    Anomaly {apiResult.anomaly_score}/100
                  </span>
                )}
              </div>

              {/* ML Model Verdict Banner */}
              {apiResult.ml_verdict && (
                <div className="mb-4 flex items-center gap-3 rounded-lg border border-purple-500/20 bg-purple-500/5 px-4 py-2.5">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-purple-400">ML Model</span>
                  <span className={`text-xs font-bold ${
                    apiResult.ml_verdict === "VERIFIED" ? "text-trust-green-glow" :
                    apiResult.ml_verdict === "CONDITIONALLY_VERIFIED" ? "text-yellow-400" :
                    apiResult.ml_verdict === "REQUIRES_REVIEW" ? "text-orange-400" :
                    "text-red-400"
                  }`}>
                    {apiResult.ml_verdict.replace(/_/g, " ")}
                  </span>
                  <span className="text-[10px] text-muted-foreground ml-auto">
                    Risk: <span className={`font-bold ${
                      apiResult.ml_fraud_risk_level === "LOW" ? "text-trust-green-glow" :
                      apiResult.ml_fraud_risk_level === "MEDIUM" ? "text-yellow-400" :
                      apiResult.ml_fraud_risk_level === "HIGH" ? "text-orange-400" :
                      "text-red-400"
                    }`}>{apiResult.ml_fraud_risk_level}</span>
                  </span>
                </div>
              )}

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {Object.entries(apiResult.fraud_patterns).map(([pattern, status]) => (
                  <div key={pattern} className={`rounded-lg px-3 py-2.5 border text-xs ${
                    status === "CONFIRMED" ? "border-red-500/30 bg-red-500/10" :
                    status === "SUSPECTED" ? "border-orange-500/30 bg-orange-500/10" :
                    status === "POSSIBLE"  ? "border-yellow-500/30 bg-yellow-500/10" :
                                            "border-border bg-secondary/20"
                  }`}>
                    <p className={`font-bold mb-0.5 ${
                      status === "CONFIRMED" ? "text-red-400" :
                      status === "SUSPECTED" ? "text-orange-400" :
                      status === "POSSIBLE"  ? "text-yellow-400" :
                                              "text-trust-green-glow"
                    }`}>
                      {status === "CONFIRMED" ? "✗" : status === "SUSPECTED" ? "⚠" : status === "POSSIBLE" ? "?" : "✓"} {status as string}
                    </p>
                    <p className="text-muted-foreground capitalize">{pattern.replace(/_/g, " ")}</p>
                  </div>
                ))}
              </div>

              {apiResult.fraud_summary && (
                <p className="mt-4 text-xs text-muted-foreground leading-relaxed border-t border-border pt-3">
                  {apiResult.fraud_summary}
                </p>
              )}

              {apiResult.fraud_flags?.length > 0 && (
                <ul className="mt-3 space-y-1">
                  {apiResult.fraud_flags.map((f: string, i: number) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                      <span className="mt-0.5 text-orange-400 shrink-0">⚠</span> {f}
                    </li>
                  ))}
                </ul>
              )}
            </motion.div>
          )}

          {/* ── All Flags ─────────────────────────────────────────────────── */}
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

          {/* ── Agent Reports (expandable) ────────────────────────────────── */}
          <div className="mt-10 space-y-3">
            <h3 className="text-lg font-semibold mb-4">Agent Reports</h3>
            {agentOutputs.map((agent, i) => (
              <motion.div
                key={agent.name}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
              >
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
                        <span className="text-sm font-bold text-trust-green-glow">{Math.round(agent.score)}/100</span>
                      ) : (
                        <span className="text-xs text-muted-foreground italic">Pending</span>
                      )}
                      <span className="text-muted-foreground text-xs">{expandedAgent === i ? "▲" : "▼"}</span>
                    </div>
                  </div>

                  {expandedAgent === i && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      className="mt-4 border-t border-border pt-4 space-y-2"
                    >
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        {agent.summary}
                      </p>
                      {agent.detail.length > 0 && (
                        <ul className="space-y-1 mt-2">
                          {agent.detail.map((d, di) => (
                            <li key={di} className="text-xs text-muted-foreground flex items-start gap-2">
                              <span className="text-trust-green-glow mt-0.5">•</span> {d}
                            </li>
                          ))}
                        </ul>
                      )}
                    </motion.div>
                  )}
                </button>
              </motion.div>
            ))}
          </div>

          {/* ── Blockchain Proof ──────────────────────────────────────────── */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="mt-10 rounded-xl border border-border bg-gradient-card p-8"
          >
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="h-6 w-6 text-trust-green-glow" />
              <h3 className="text-lg font-semibold">Blockchain Proof</h3>
              {apiResult?.tx_hash ? (
                <span className="ml-auto text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full border border-trust-green-glow/40 text-trust-green-glow bg-trust-green-glow/10">
                  Confirmed ✓
                </span>
              ) : (
                <span className="ml-auto text-xs text-muted-foreground italic">Pending blockchain write</span>
              )}
            </div>
            <div className="space-y-3 text-sm">
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Transaction Hash</span>
                {apiResult?.tx_hash ? (
                  <a
                    href={`https://amoy.polygonscan.com/tx/0x${apiResult.tx_hash.replace(/^0x/, "")}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-xs text-accent hover:underline bg-secondary/50 px-3 py-1.5 rounded break-all inline-flex items-center gap-1.5"
                  >
                    0x{apiResult.tx_hash.replace(/^0x/, "").slice(0, 8)}…{apiResult.tx_hash.replace(/^0x/, "").slice(-8)}
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                ) : (
                  <code className="font-mono text-xs text-muted-foreground bg-secondary/50 px-3 py-1.5 rounded">—</code>
                )}
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Record ID</span>
                <span className="text-foreground">{apiResult?.record_id != null ? `#${apiResult.record_id}` : "—"}</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Block Number</span>
                <span className="text-foreground">{apiResult?.block_number ?? "—"}</span>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                <span className="text-muted-foreground min-w-[120px]">Network</span>
                <span className="text-foreground">Polygon Amoy Testnet</span>
              </div>
              {apiResult?.contract_address && (
                <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3">
                  <span className="text-muted-foreground min-w-[120px]">Contract</span>
                  <a
                    href={`https://amoy.polygonscan.com/address/${apiResult.contract_address}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-xs text-accent hover:underline inline-flex items-center gap-1.5"
                  >
                    {apiResult.contract_address.slice(0, 8)}…{apiResult.contract_address.slice(-6)}
                    <ExternalLink className="h-3 w-3 shrink-0" />
                  </a>
                </div>
              )}
            </div>
            {apiResult?.tx_hash && (
              <a
                href={`https://amoy.polygonscan.com/tx/0x${apiResult.tx_hash.replace(/^0x/, "")}`}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex items-center gap-2 text-sm text-accent hover:underline"
              >
                View on Explorer <ExternalLink className="h-3.5 w-3.5" />
              </a>
            )}
          </motion.div>

          <div className="mt-8 flex justify-end">
            <Link
              to="/verify"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-secondary/50 px-5 py-2.5 text-sm font-medium transition-all hover:bg-secondary"
            >
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