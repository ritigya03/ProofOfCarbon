"""
baseline.py — Computes historical baseline metrics for carbon credit additionality assessment.

"Additionality" is the core question in carbon markets:
Would this forest have survived WITHOUT the carbon credit funding?
If yes → the credits are not additional → they are fraudulent.

Data used:
  Real path:  India State of Forest Report (FSI) historical records + state deforestation rates
  Mock path:  Deterministic lookup tables based on real published India statistics

Key concepts:
  - Deforestation pressure:  How likely was this forest to be cleared without intervention?
  - Baseline forest loss rate: Historical % loss per year for this state/forest type
  - Counterfactual:  What would the area look like in 10 years without the project?
  - Permanence risk: How likely is the sequestered carbon to be re-released?
"""

import logging
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# India State-Level Deforestation Statistics
# Sources:
#   FSI India State of Forest Report 2021 & 2023
#   MoEFCC Annual Report 2022-23
#   WRI Global Forest Watch India data
#
# Format: state → {annual_loss_rate_pct, pressure_level, primary_drivers, data_year}
# annual_loss_rate_pct = average % of forest area lost per year (2015-2023)
# ─────────────────────────────────────────────────────────────────────────────

INDIA_STATE_DEFORESTATION = {
    # Northeast — highest pressure due to jhum (shifting cultivation) + infrastructure
    "Arunachal Pradesh":   {"annual_loss_pct": 0.41, "pressure": "HIGH",   "drivers": ["jhum_cultivation", "infrastructure", "encroachment"]},
    "Manipur":             {"annual_loss_pct": 0.89, "pressure": "CRITICAL","drivers": ["jhum_cultivation", "insurgency_related_clearing", "infrastructure"]},
    "Meghalaya":           {"annual_loss_pct": 0.62, "pressure": "HIGH",   "drivers": ["coal_mining", "jhum_cultivation", "limestone_quarrying"]},
    "Mizoram":             {"annual_loss_pct": 0.55, "pressure": "HIGH",   "drivers": ["jhum_cultivation", "bamboo_harvesting"]},
    "Nagaland":            {"annual_loss_pct": 0.73, "pressure": "HIGH",   "drivers": ["jhum_cultivation", "infrastructure", "illegal_logging"]},
    "Tripura":             {"annual_loss_pct": 0.38, "pressure": "MEDIUM", "drivers": ["agricultural_expansion", "rubber_plantation"]},
    "Assam":               {"annual_loss_pct": 0.44, "pressure": "HIGH",   "drivers": ["tea_garden_expansion", "agricultural_encroachment", "floods"]},
    "Sikkim":              {"annual_loss_pct": 0.12, "pressure": "LOW",    "drivers": ["hydropower_projects", "road_construction"]},

    # Central India — significant pressure from mining + agriculture
    "Madhya Pradesh":      {"annual_loss_pct": 0.28, "pressure": "MEDIUM", "drivers": ["mining", "agricultural_expansion", "fuelwood"]},
    "Chhattisgarh":        {"annual_loss_pct": 0.31, "pressure": "MEDIUM", "drivers": ["mining", "left_wing_extremism_area_clearing", "agriculture"]},
    "Jharkhand":           {"annual_loss_pct": 0.35, "pressure": "MEDIUM", "drivers": ["mining", "industrial_expansion", "fuelwood"]},
    "Odisha":              {"annual_loss_pct": 0.29, "pressure": "MEDIUM", "drivers": ["mining", "agricultural_expansion", "cyclone_damage"]},

    # Western Ghats — moderate pressure, high biodiversity value
    "Karnataka":           {"annual_loss_pct": 0.19, "pressure": "MEDIUM", "drivers": ["plantation_conversion", "encroachment", "infrastructure"]},
    "Kerala":              {"annual_loss_pct": 0.14, "pressure": "LOW",    "drivers": ["plantation_conversion", "landslides", "urbanisation"]},
    "Tamil Nadu":          {"annual_loss_pct": 0.21, "pressure": "MEDIUM", "drivers": ["encroachment", "plantation_conversion", "urban_expansion"]},
    "Goa":                 {"annual_loss_pct": 0.16, "pressure": "MEDIUM", "drivers": ["mining", "infrastructure", "tourism_development"]},
    "Maharashtra":         {"annual_loss_pct": 0.22, "pressure": "MEDIUM", "drivers": ["agricultural_expansion", "infrastructure", "encroachment"]},

    # Himalayan states — lower pressure but high permanence risk (landslides, fire)
    "Uttarakhand":         {"annual_loss_pct": 0.17, "pressure": "LOW",    "drivers": ["forest_fire", "infrastructure", "tourism"]},
    "Himachal Pradesh":    {"annual_loss_pct": 0.11, "pressure": "LOW",    "drivers": ["forest_fire", "apple_orchard_expansion", "infrastructure"]},
    "Jammu & Kashmir":     {"annual_loss_pct": 0.09, "pressure": "LOW",    "drivers": ["forest_fire", "infrastructure"]},

    # East India
    "West Bengal":         {"annual_loss_pct": 0.26, "pressure": "MEDIUM", "drivers": ["agricultural_expansion", "urbanisation", "cyclone_damage"]},
    "Bihar":               {"annual_loss_pct": 0.18, "pressure": "LOW",    "drivers": ["fuelwood", "agricultural_expansion"]},

    # Dry / low forest states
    "Rajasthan":           {"annual_loss_pct": 0.07, "pressure": "LOW",    "drivers": ["overgrazing", "fuelwood", "drought"]},
    "Gujarat":             {"annual_loss_pct": 0.13, "pressure": "LOW",    "drivers": ["industrial_expansion", "agricultural_conversion"]},
    "Andhra Pradesh":      {"annual_loss_pct": 0.24, "pressure": "MEDIUM", "drivers": ["agricultural_expansion", "infrastructure", "encroachment"]},
    "Telangana":           {"annual_loss_pct": 0.20, "pressure": "MEDIUM", "drivers": ["urbanisation", "agricultural_expansion"]},

    # Default for unmapped/union territories
    "_default":            {"annual_loss_pct": 0.25, "pressure": "MEDIUM", "drivers": ["unknown"]},
}


# ─────────────────────────────────────────────────────────────────────────────
# Forest type permanence risk
# How likely is carbon stored in this forest type to be re-released
# (fire, disease, drought, illegal logging)?
# Sources: IPCC Guidelines for National Greenhouse Gas Inventories (2006, 2019)
#          MoEFCC Forest Carbon Stock data
# ─────────────────────────────────────────────────────────────────────────────

FOREST_TYPE_PERMANENCE_RISK = {
    "dense":            {"permanence_risk": "LOW",    "reversal_risk_pct": 5,  "avg_carbon_t_ha": 120},
    "moderately_dense": {"permanence_risk": "LOW",    "reversal_risk_pct": 8,  "avg_carbon_t_ha": 75},
    "open":             {"permanence_risk": "MEDIUM", "reversal_risk_pct": 18, "avg_carbon_t_ha": 35},
    "scrub":            {"permanence_risk": "HIGH",   "reversal_risk_pct": 35, "avg_carbon_t_ha": 12},
    "mangrove":         {"permanence_risk": "MEDIUM", "reversal_risk_pct": 15, "avg_carbon_t_ha": 160},
    "dry_deciduous":    {"permanence_risk": "HIGH",   "reversal_risk_pct": 28, "avg_carbon_t_ha": 45},
    "moist_deciduous":  {"permanence_risk": "LOW",    "reversal_risk_pct": 10, "avg_carbon_t_ha": 90},
    "temperate":        {"permanence_risk": "LOW",    "reversal_risk_pct": 8,  "avg_carbon_t_ha": 105},
    "sal":              {"permanence_risk": "LOW",    "reversal_risk_pct": 10, "avg_carbon_t_ha": 95},
    "_default":         {"permanence_risk": "MEDIUM", "reversal_risk_pct": 20, "avg_carbon_t_ha": 60},
}


def get_state_baseline(state: str) -> dict:
    """
    Returns historical deforestation statistics for an Indian state.
    Normalises state name for case/spacing issues.
    """
    # Normalise: "karnataka" → "Karnataka", "WEST BENGAL" → "West Bengal"
    normalised = state.strip().title()
    data = INDIA_STATE_DEFORESTATION.get(normalised, INDIA_STATE_DEFORESTATION["_default"])
    return {
        "state": normalised,
        "annual_loss_pct": data["annual_loss_pct"],
        "deforestation_pressure": data["pressure"],
        "primary_drivers": data["drivers"],
        "data_source": "FSI_ISFR_2023_mock",  # replace with "FSI_ISFR_2023" when real data loaded
    }


def get_forest_type_stats(forest_type: str) -> dict:
    """
    Returns permanence risk and carbon stock data for a given forest type.
    Tries to match forest_type string to known keys (fuzzy).
    """
    ft = forest_type.lower().replace(" ", "_").replace("-", "_") if forest_type else "_default"

    # Fuzzy match common variations
    mapping = {
        "evergreen": "dense",
        "semi_evergreen": "dense",
        "tropical_wet": "dense",
        "dense_forest": "dense",
        "very_dense": "dense",
        "moderate": "moderately_dense",
        "mixed": "moderately_dense",
        "open_forest": "open",
        "degraded": "scrub",
        "plantation": "open",
        "teak": "moist_deciduous",
        "bamboo": "open",
    }
    resolved = mapping.get(ft, ft)
    data = FOREST_TYPE_PERMANENCE_RISK.get(resolved, FOREST_TYPE_PERMANENCE_RISK["_default"])

    return {
        "forest_type_resolved": resolved,
        "permanence_risk": data["permanence_risk"],
        "reversal_risk_pct": data["reversal_risk_pct"],
        "avg_carbon_stock_t_ha": data["avg_carbon_t_ha"],
    }


def compute_additionality_metrics(
    state: str,
    forest_type: str,
    claimed_ha: float,
    project_start_year: int = 2020,
    credit_period_years: int = 10,
) -> dict:
    """
    Computes quantitative additionality metrics.

    Additionality = the forest would NOT have survived without the project.
    Calculated as: projected loss without project over the credit period.

    Args:
        state: Indian state name
        forest_type: type of forest (dense, open, mangrove, etc.)
        claimed_ha: total claimed project area in hectares
        project_start_year: year the project claims to have started
        credit_period_years: how many years of credits are being claimed

    Returns:
        dict with baseline scenario, counterfactual loss, and additionality score
    """
    state_data   = get_state_baseline(state)
    ft_data      = get_forest_type_stats(forest_type)

    annual_loss_rate  = state_data["annual_loss_pct"] / 100
    pressure          = state_data["deforestation_pressure"]
    reversal_risk_pct = ft_data["reversal_risk_pct"]
    carbon_t_ha       = ft_data["avg_carbon_stock_t_ha"]

    # Projected forest loss over credit period WITHOUT intervention
    counterfactual_loss_ha = claimed_ha * annual_loss_rate * credit_period_years
    counterfactual_loss_ha = min(counterfactual_loss_ha, claimed_ha)  # can't lose more than you have

    # Projected carbon at risk (tonnes CO2e)
    carbon_at_risk_t = counterfactual_loss_ha * carbon_t_ha

    # Additionality score: how much of the claimed area is genuinely under threat
    # HIGH pressure + HIGH loss rate = HIGH additionality (credits are justified)
    # LOW pressure + LOW loss rate = LOW additionality (forest would have survived anyway)
    additionality_score = min(100, (annual_loss_rate * 100 * 10))  # scaled 0-100

    # Permanence buffer: % of credits that should be held in a buffer pool
    # to account for reversal risk (IPCC / Verra VCS methodology)
    buffer_pct = reversal_risk_pct

    flags = []
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
    if ft_data["permanence_risk"] == "HIGH":
        flags.append(
            f"{ft_data['forest_type_resolved'].replace('_', ' ').title()} forest has high reversal risk "
            f"({reversal_risk_pct}%) — significant buffer pool required."
        )
    if counterfactual_loss_ha < claimed_ha * 0.05:
        flags.append(
            "Very low projected forest loss in baseline scenario — "
            "carbon credits may represent minimal real-world impact."
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
        "data_source":                "FSI_ISFR_2023_WRI_GFW_mock",
    }