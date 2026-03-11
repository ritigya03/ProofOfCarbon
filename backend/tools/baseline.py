"""
baseline.py — Computes historical baseline metrics for carbon credit additionality assessment.

"Additionality" is the core question in carbon markets:
Would this forest have survived WITHOUT the carbon credit funding?
If yes → the credits are not additional → they are fraudulent.

Data used:
  State deforestation rates: data/reference/india_state_deforestation.csv
    Sources: FSI India State of Forest Report 2023, MoEFCC Annual Report 2022-23, WRI GFW India
  Forest type permanence:   data/reference/forest_type_permanence.csv
    Sources: IPCC Guidelines for National GHG Inventories (2006, 2019), MoEFCC Forest Carbon Stock data

Key concepts:
  - Deforestation pressure:  How likely was this forest to be cleared without intervention?
  - Baseline forest loss rate: Historical % loss per year for this state/forest type
  - Counterfactual:  What would the area look like in 10 years without the project?
  - Permanence risk: How likely is the sequestered carbon to be re-released?
"""

import csv
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Resolve default data paths ────────────────────────────────────────────────
# Paths can be overridden by env vars for flexibility in different environments.
_THIS_DIR   = Path(__file__).parent.parent   # backend/
_STATE_CSV  = Path(os.getenv(
    "STATE_DEFORESTATION_CSV",
    str(_THIS_DIR / "data" / "reference" / "india_state_deforestation.csv")
))
_FOREST_CSV = Path(os.getenv(
    "FOREST_TYPE_CSV",
    str(_THIS_DIR / "data" / "reference" / "forest_type_permanence.csv")
))


# ── Loaders (run once at module import) ───────────────────────────────────────

def _load_state_data() -> dict:
    """
    Load state-level deforestation data from CSV.
    Returns a dict keyed by state name (title-cased).
    Format: { "Karnataka": { "annual_loss_pct": 0.19, "pressure": "MEDIUM", "drivers": [...] }, ... }
    """
    if not _STATE_CSV.exists():
        raise FileNotFoundError(
            f"State deforestation CSV not found at: {_STATE_CSV}\n"
            f"  Expected: data/reference/india_state_deforestation.csv\n"
            f"  Override path with env var STATE_DEFORESTATION_CSV"
        )

    data = {}
    with open(_STATE_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["state"].strip()
            # Support both old and new schemas
            loss_pct = row.get("annual_deforestation_rate_pct") or row.get("annual_loss_pct", "0.2")
            pressure = row.get("deforestation_pressure_level") or row.get("pressure", "MEDIUM")
            drivers_raw = row.get("drivers") or row.get("notes", "General human pressure")
            
            data[key] = {
                "annual_loss_pct": float(loss_pct),
                "pressure":        pressure.strip().upper(),
                "drivers":         [d.strip() for d in drivers_raw.split("|")],
                "data_year":       row.get("data_year", "2023").strip(),
            }

    logger.info(f"[baseline] Loaded {len(data)} state rows from {_STATE_CSV.name}")
    return data


def _load_forest_type_data() -> dict:
    """
    Load forest type permanence data from CSV.
    Returns a dict keyed by forest type name.
    Format: { "dense": { "permanence_risk": "LOW", "reversal_risk_pct": 5, "avg_carbon_t_ha": 120 }, ... }
    """
    if not _FOREST_CSV.exists():
        raise FileNotFoundError(
            f"Forest type CSV not found at: {_FOREST_CSV}\n"
            f"  Expected: data/reference/forest_type_permanence.csv\n"
            f"  Override path with env var FOREST_TYPE_CSV"
        )

    data = {}
    with open(_FOREST_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            key = row["forest_type"].strip()
            # Support both old and new schemas
            score = float(row.get("permanence_score") or 0.75)
            carbon = int(float(row.get("avg_carbon_density_tC_ha") or row.get("avg_carbon_t_ha", 150)))
            
            # Map score to risk (low risk if high score)
            risk_level = "LOW" if score > 0.7 else "MEDIUM" if score > 0.4 else "HIGH"
            reversal_pct = int((1.0 - score) * 100)

            data[key] = {
                "permanence_risk":    risk_level,
                "reversal_risk_pct":  reversal_pct,
                "avg_carbon_t_ha":    carbon,
            }

    logger.info(f"[baseline] Loaded {len(data)} forest type rows from {_FOREST_CSV.name}")
    return data


# Loaded once at module import — same performance as Python dicts
INDIA_STATE_DEFORESTATION   = _load_state_data()
FOREST_TYPE_PERMANENCE_RISK = _load_forest_type_data()


# ── Public helpers ────────────────────────────────────────────────────────────

def get_state_baseline(state: str) -> dict:
    """
    Returns historical deforestation statistics for an Indian state.
    Normalises state name for case/spacing issues.
    Falls back to _default row if state is not in the CSV.
    """
    normalised = state.strip().title()
    # Safe lookup with fallback to first row or reasonable defaults if _default is missing
    if normalised in INDIA_STATE_DEFORESTATION:
        data = INDIA_STATE_DEFORESTATION[normalised]
    elif "_default" in INDIA_STATE_DEFORESTATION:
        data = INDIA_STATE_DEFORESTATION["_default"]
    else:
        # Emergency fallback if CSV is mangled
        data = {
            "annual_loss_pct": 0.35,
            "pressure": "MEDIUM",
            "drivers": ["General human pressure"],
            "data_year": "2023"
        }
    return {
        "state":                  normalised,
        "annual_loss_pct":       data["annual_loss_pct"],
        "deforestation_pressure": data["pressure"],
        "primary_drivers":       data["drivers"],
        "data_source":           "FSI_ISFR_2023_WRI_GFW",
    }


def get_forest_type_stats(forest_type: str) -> dict:
    """
    Returns permanence risk and carbon stock data for a given forest type.
    Tries to match forest_type string to known keys (fuzzy).
    Falls back to _default row if no match.
    """
    ft = forest_type.lower().replace(" ", "_").replace("-", "_") if forest_type else "_default"

    # Fuzzy match common variations
    mapping = {
        "evergreen":        "dense",
        "semi_evergreen":   "dense",
        "tropical_wet":     "dense",
        "dense_forest":     "dense",
        "very_dense":       "dense",
        "moderate":         "moderately_dense",
        "mixed":            "moderately_dense",
        "open_forest":      "open",
        "degraded":         "scrub",
        "plantation":       "open",
        "teak":             "moist_deciduous",
        "bamboo":           "open",
        "native":           "moist_deciduous",
        "broadleaf":        "moist_deciduous",
        "native_broadleaf": "moist_deciduous",
    }
    # Safe lookup for forest types
    resolved = mapping.get(ft, ft)
    if resolved in FOREST_TYPE_PERMANENCE_RISK:
        data = FOREST_TYPE_PERMANENCE_RISK[resolved]
    elif "_default" in FOREST_TYPE_PERMANENCE_RISK:
        data = FOREST_TYPE_PERMANENCE_RISK["_default"]
    else:
        data = {
            "permanence_risk": "MEDIUM",
            "reversal_risk_pct": 15,
            "avg_carbon_t_ha": 150
        }

    return {
        "forest_type_resolved": resolved,
        "permanence_risk":      data["permanence_risk"],
        "reversal_risk_pct":    data["reversal_risk_pct"],
        "avg_carbon_stock_t_ha": data["avg_carbon_t_ha"],
    }


def compute_additionality_metrics(
    state: str,
    forest_type: str,
    claimed_ha: float,
    project_start_year: int = 2020,
    credit_period_years: int = 10,
    project_type: str = "REDD+",
) -> dict:
    """
    Computes quantitative additionality metrics.

    For REDD+: 
    Additionality = the forest would NOT have survived without the project.
    Calculated as: projected loss without project over the credit period.

    For ARR:
    Additionality = the forest would NOT have grown back without the project.
    Calculated as: sequestration potential minus counterfactual natural regeneration.

    Args:
        state: Indian state name
        forest_type: type of forest (dense, open, mangrove, etc.)
        claimed_ha: total claimed project area in hectares
        project_start_year: year the project claims to have started
        credit_period_years: how many years of credits are being claimed
        project_type: "ARR" or "REDD+"

    Returns:
        dict with baseline scenario, counterfactual loss/growth, and additionality score
    """
    state_data   = get_state_baseline(state)
    ft_data      = get_forest_type_stats(forest_type)

    annual_loss_rate  = state_data["annual_loss_pct"] / 100
    pressure          = state_data["deforestation_pressure"]
    reversal_risk_pct = ft_data["reversal_risk_pct"]
    carbon_t_ha       = ft_data["avg_carbon_stock_t_ha"]

    flags = []

    if project_type == "ARR":
        # ARR Calculation
        # Counterfactual: How much would it have grown naturally?
        # Higher pressure (human activity) = lower natural regeneration potential.
        pressure_regeneration_map = {
            "CRITICAL": 0.4, # tC/ha/yr - Highly unlikely to recover naturally
            "HIGH":     0.8,
            "MEDIUM":   1.2,
            "LOW":      2.0  # tC/ha/yr - Likely to recover if left alone
        }
        counterfactual_regeneration_rate = pressure_regeneration_map.get(pressure, 1.2)
        counterfactual_growth_t = claimed_ha * counterfactual_regeneration_rate * credit_period_years
        
        # Project potential: Use the specific carbon stock for this forest type.
        # Mangroves and Moist Deciduous sequester much faster than Scrub/Dry.
        # We assume it takes 20 years to reach "average" stock for a new plantation (avg/20 per yr).
        sequestration_rate_per_yr = carbon_t_ha / 20.0
        project_potential_t = claimed_ha * sequestration_rate_per_yr * credit_period_years
        
        # Additionality is the "delta" created by the project intervention
        additionality_t = max(0.0, project_potential_t - counterfactual_growth_t)
        
        # Additionality Score (%)
        additionality_score = min(100.0, (additionality_t / project_potential_t * 100)) if project_potential_t > 0 else 0.0
        
        counterfactual_loss_ha = 0 # Not applicable to ARR
        carbon_at_risk_t = additionality_t # In ARR, the "risk" is the lost sequestration potential
        
        if additionality_score < 40:
            flags.append(
                f"High natural regeneration potential in {state} ({counterfactual_regeneration_rate} tC/ha/yr) — "
                f"ARR additionality score ({additionality_score:.1f}) is weak."
            )
        else:
            flags.append(
                f"Low natural regeneration baseline in {state} ({counterfactual_regeneration_rate} tC/ha/yr) — "
                f"strong additionality case for ARR."
            )

    else:
        # REDD+ Calculation (Existing)
        # Projected forest loss over credit period WITHOUT intervention
        counterfactual_loss_ha = claimed_ha * annual_loss_rate * credit_period_years
        counterfactual_loss_ha = min(counterfactual_loss_ha, claimed_ha)

        # Projected carbon at risk (tonnes CO2e)
        carbon_at_risk_t = counterfactual_loss_ha * carbon_t_ha

        # Additionality score: 0-100 based on threat
        # If loss is 0.5%/yr, score is 0.5 * 80 * 2 = 80. 
        # If loss is 1.15%/yr (Meghalaya), score is 1.15 * 80 * 1 = 92.
        additionality_score = min(100.0, (annual_loss_rate * 100 * 80))

        if pressure == "LOW" and annual_loss_rate < 0.15:
            flags.append(
                f"Low deforestation pressure in {state} ({annual_loss_rate*100:.2f}%/yr) — "
                f"additionality may be weak. Forest likely to survive without intervention."
            )
        if pressure == "CRITICAL":
            flags.append(
                f"CRITICAL deforestation pressure in {state} — "
                f"strong additionality case if project is genuine."
            )
        if counterfactual_loss_ha < claimed_ha * 0.05:
            flags.append(
                "Very low projected forest loss in baseline scenario — "
                "carbon credits may represent minimal real-world impact."
            )

    # Permanence buffer %
    buffer_pct = reversal_risk_pct

    if ft_data["permanence_risk"] == "HIGH":
        flags.append(
            f"{ft_data['forest_type_resolved'].replace('_', ' ').title()} forest has high reversal risk "
            f"({reversal_risk_pct}%) — significant buffer pool required."
        )

    return {
        # State baseline
        "state":                      state_data["state"],
        "annual_deforestation_pct":   state_data["annual_loss_pct"],
        "deforestation_pressure":     pressure,
        "primary_drivers":            state_data["primary_drivers"],

        # Forest type
        "forest_type_resolved":       ft_data["forest_type_resolved"],
        "permanence_risk":            ft_data["permanence_risk"],
        "avg_carbon_stock_t_ha":      carbon_t_ha,

        # Counterfactual scenario
        "project_start_year":         project_start_year,
        "credit_period_years":        credit_period_years,
        "counterfactual_loss_ha":     round(counterfactual_loss_ha, 2),
        "counterfactual_loss_pct":    round((counterfactual_loss_ha / claimed_ha * 100) if claimed_ha else 0, 1),
        "carbon_at_risk_tonnes_co2e": round(carbon_at_risk_t, 1),

        # Scores
        "additionality_score":        round(additionality_score, 1),  # 0-100
        "required_buffer_pct":        buffer_pct,

        # Flags
        "baseline_flags":             flags,
        "data_source":                "FSI_ISFR_2023_WRI_GFW",
        "project_type":               project_type
    }
