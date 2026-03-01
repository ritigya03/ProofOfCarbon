// src/lib/api.ts
// Shared types that mirror backend api/schemas.py.
// Import these in any component that consumes the /analyze response.

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type VerdictType =
  | "VERIFIED"
  | "CONDITIONALLY_VERIFIED"
  | "REQUIRES_REVIEW"
  | "REJECTED";

export type VegetationClass =
  | "DENSE_FOREST"
  | "MODERATE_FOREST"
  | "SPARSE_VEGETATION"
  | "DEGRADED"
  | "BARE_GROUND";

export type NdviTrend = "INCREASING" | "STABLE" | "DECREASING";

export type FraudPatternStatus = "CONFIRMED" | "SUSPECTED" | "POSSIBLE" | "CLEAR";

export interface FraudPatterns {
  phantom_forest: FraudPatternStatus;
  area_inflation: FraudPatternStatus;
  signal_contradiction: FraudPatternStatus;
  protected_area_laundering: FraudPatternStatus;
  round_number_anomaly: FraudPatternStatus;
  administrative_mismatch: FraudPatternStatus;
}

export interface AnalyzeResponse {
  // ── Identity
  project_name: string | null;
  company_name: string | null;
  state: string | null;
  forest_type: string | null;

  // ── Stage 1: Spatial (always present)
  claimed_hectares: number;
  verified_hectares: number;
  overlap_percent: number;
  protected_area_overlap_ha: number;
  risk_level: RiskLevel;
  trust_score: number;
  summary: string;
  all_flags: string[];
  analysis_flags: string[];
  red_flags: string[];

  // ── Stage 2: Satellite (null if skipped/failed)
  ndvi_current_mean: number | null;
  ndvi_historical_mean: number | null;
  ndvi_trend: NdviTrend | null;
  ndvi_anomaly_score: number | null;
  ndvi_pixel_count: number | null;
  ndvi_data_source: string | null;
  vegetation_class: VegetationClass | null;
  satellite_risk_level: RiskLevel | null;
  satellite_trust_modifier: number | null;
  satellite_flags: string[];
  satellite_summary: string | null;

  // ── Stage 3: Fraud (null if skipped/failed)
  anomaly_score: number | null;
  fraud_risk_level: RiskLevel | null;
  fraud_patterns: FraudPatterns | null;
  fraud_flags: string[];
  fraud_summary: string | null;

  // ── Stage 4: Final verdict (null if skipped/failed)
  final_verdict: VerdictType | null;
  final_trust_score: number | null;
  final_risk_level: RiskLevel | null;
  confidence: "HIGH" | "MEDIUM" | "LOW" | null;
  key_findings: string[];
  recommendation: string | null;
  verification_summary: string | null;
}

// ── Health check utility ───────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      signal: AbortSignal.timeout(3000),
    });
    const data = await res.json();
    return data.agent_ready === true;
  } catch {
    return false;
  } 
}