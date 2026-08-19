# make_buildings_by_sector_from_end_use_energy_four_panel_region.py
# 2×2 stacked bars for buildings energy (Residential / Commercial) under
# Current Policy vs Net-Zero — with a --region option.
#
# Inputs (required):
#   end_use_energy_ref.csv   -> Current Policy Scenario (pyam long format)
#   end_use_energy.csv       -> Net-Zero Scenario (pyam long format)
# Inputs (optional; improves R vs C split for elec & gas):
#   ref_pyam.csv, nz_pyam.csv  (pyam wide-year tables)
#
# Usage:
#   python make_buildings_by_sector_from_end_use_energy_four_panel_region.py --region CAN
#   python make_buildings_by_sector_from_end_use_energy_four_panel_region.py --region AB
# Optional:
#   --ref_eu end_use_energy_ref.csv --nz_eu end_use_energy.csv --ref_py ref_pyam.csv --nz_py nz_pyam.csv --out my_plot.png
#
# Notes:
# - If --region CAN (or ALL/CANADA), aggregates across all provinces.
# - If a specific region (e.g., AB) is provided, filters to that region.
# - Converts PJ -> EJ (EJ = PJ / 1000).
# - Electricity & Natural Gas are split into Residential/Commercial using
#   sector shares from PYAM if present for the chosen region; otherwise 50/50.

import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

BAR_WIDTH = 4.0

# Defaults (can be overridden by CLI)
END_USE_REF_DEFAULT = "end_use_energy_ref.csv"
END_USE_NZ_DEFAULT  = "end_use_energy.csv"
PYAM_REF_DEFAULT    = "ref_pyam.csv"   # optional
PYAM_NZ_DEFAULT     = "nz_pyam.csv"    # optional

# ---------- Helpers ----------
def normalize_region(region: str | None) -> str:
    if region is None:
        return "CAN"
    r = str(region).strip().upper()
    synonyms = {"ALL": "CAN", "CANADA": "CAN", "ALL_CANADA": "CAN"}
    return synonyms.get(r, r)

def find_col(df: pd.DataFrame, target: str) -> str | None:
    """Find a column name case-insensitively. Returns None if not found."""
    tl = target.lower()
    for c in df.columns:
        if c.lower() == tl:
            return c
    return None

def load_end_use(path: str, scenario_label: str, region: str) -> pd.DataFrame:
    """Load end-use long-format CSV and filter/aggregate to region.
       Expects columns similar to pyam long: model, scenario, region, variable, unit, time, value.
    """
    df = pd.read_csv(path)
    unit_col = find_col(df, "unit") or "unit"
    region_col = find_col(df, "region")  # may be None in some datasets
    time_col = find_col(df, "time") or "time"
    variable_col = find_col(df, "variable") or "variable"
    value_col = find_col(df, "value") or "value"

    # Keep only PJ
    if unit_col in df.columns:
        df = df[df[unit_col] == "PJ"].copy()

    # Region filter / aggregation
    region_norm = normalize_region(region)
    if region_col and region_col in df.columns:
        if region_norm == "CAN":
            # Aggregate across regions -> Canada
            grp_cols = [time_col, variable_col, unit_col]
            summed = (df.groupby(grp_cols, as_index=False)[value_col].sum()
                        .assign(ScenarioLabel=scenario_label, RegionLabel="CAN"))
            return summed
        else:
            mask = df[region_col].astype(str).str.upper() == region_norm
            sub = df.loc[mask].copy()
            if sub.empty:
                available = ", ".join(sorted(df[region_col].dropna().astype(str).unique()))
                raise ValueError(f"Region '{region_norm}' not found in {path}. Available Region values: {available}")
            sub = sub.assign(ScenarioLabel=scenario_label, RegionLabel=region_norm)
            return sub
    else:
        # No region column — assume already national; just tag the scenario.
        return df.assign(ScenarioLabel=scenario_label, RegionLabel=region_norm)

def load_pyam(path: str, scenario_label: str, region: str) -> pd.DataFrame | None:
    """Load pyam wide-year table and melt to long; then filter/aggregate to region."""
    p = Path(path)
    if not p.exists():
        return None
    df = pd.read_csv(p)
    region_col = find_col(df, "Region") or find_col(df, "region")
    year_cols = [c for c in df.columns if str(c).isdigit()]
    long = df.melt(
        id_vars=[c for c in ["Model", "Scenario", region_col, "Variable", "Unit"] if c is not None and c in df.columns],
        value_vars=year_cols,
        var_name="Year",
        value_name="PJ",
    )
    if "Year" in long.columns:
        long["Year"] = long["Year"].astype(int)
    long["ScenarioLabel"] = scenario_label

    region_norm = normalize_region(region)
    if region_col and region_col in long.columns:
        if region_norm == "CAN":
            # aggregate across Region
            long = (long.groupby(["ScenarioLabel","Variable","Unit","Year"], as_index=False)["PJ"].sum()
                        .assign(Region="CAN"))
        else:
            mask = long[region_col].astype(str).str.upper() == region_norm
            long = long.loc[mask].copy()
            if long.empty:
                avail = ", ".join(sorted(df[region_col].dropna().astype(str).unique()))
                raise ValueError(f"Region '{region_norm}' not found in {path}. Available Region values: {avail}")
    else:
        long["Region"] = region_norm
    return long

def sum_value(df: pd.DataFrame, variable: str) -> float:
    """Sum a single variable across all rows (already region-filtered/aggregated)."""
    var_col = find_col(df, "variable") or "variable"
    val_col = find_col(df, "value") or "value"
    return float(df.loc[df[var_col] == variable, val_col].sum())

# ---------- Compute Residential/Commercial shares (from PYAM, if present) ----------
def compute_sector_shares(pyam_all: pd.DataFrame | None) -> pd.DataFrame | None:
    """Return DataFrame with columns:
       ScenarioLabel, Year, share_R_elec, share_C_elec, share_R_ng, share_C_ng
       or None if PYAM files are not provided.
       Assumes pyam_all already filtered/aggregated to the requested region.
    """
    if pyam_all is None or pyam_all.empty:
        return None

    def shares_for(pair_map: dict[str, str], col_prefix: str) -> pd.DataFrame:
        subset = pyam_all[pyam_all["Variable"].isin(pair_map.keys())].copy()
        subset["FuelRC"] = subset["Variable"].map(pair_map)
        sums = subset.groupby(["ScenarioLabel", "Year", "FuelRC"], as_index=False)["PJ"].sum()
        wide = sums.pivot_table(index=["ScenarioLabel", "Year"], columns="FuelRC", values="PJ", aggfunc="sum").fillna(0)
        r = wide.get("R", 0)
        c = wide.get("C", 0)
        total = r + c
        share_r = np.where(total > 0, r / total, 0.5)
        share_c = 1.0 - share_r
        out = pd.DataFrame({
            "ScenarioLabel": wide.index.get_level_values("ScenarioLabel"),
            "Year": wide.index.get_level_values("Year"),
            f"share_R_{col_prefix}": share_r,
            f"share_C_{col_prefix}": share_c,
        })
        return out

    elec_map = {
        "Activity|residential|E_R_ELC": "R",
        "Activity|commercial|E_C_ELC": "C",
    }
    ng_map = {
        "Activity|residential|F_R_NG": "R",
        "Activity|commercial|F_C_NG": "C",
    }

    elec = shares_for(elec_map, "elec")
    ng = shares_for(ng_map, "ng")
    shares = elec.merge(ng, on=["ScenarioLabel", "Year"], how="outer")
    return shares

# ---------- Build table with sector split ----------
def build_table(end_use_all: pd.DataFrame, shares: pd.DataFrame | None) -> pd.DataFrame:
    rows = []

    time_col = find_col(end_use_all, "time") or "time"
    scen_col = "ScenarioLabel"

    for (scen, year), grp in end_use_all.groupby([scen_col, time_col]):
        year = int(year)

        # Default shares (if no PYAM)
        r_elec = c_elec = 0.5
        r_ng = c_ng = 0.5

        if shares is not None:
            s = shares[(shares["ScenarioLabel"] == scen) & (shares["Year"] == year)]
            if len(s) == 1:
                r_elec = float(s["share_R_elec"])
                c_elec = float(s["share_C_elec"])
                r_ng   = float(s["share_R_ng"])
                c_ng   = float(s["share_C_ng"])

        # Electricity end-uses (already region-aggregated/filtered)
        e_space_cooling = sum_value(grp, "final energy|space cooling|electricity")
        e_water_heating = sum_value(grp, "final energy|water heating|electricity")
        e_space_heating = sum_value(grp, "final energy|space heating|electricity")
        e_lighting      = sum_value(grp, "final energy|lighting|electricity")
        e_rf            = (
            sum_value(grp, "final energy|refrigerator|electricity")
            + sum_value(grp, "final energy|freezer|electricity")
        )
        e_other = (
            sum_value(grp, "final energy|other electrical|electricity")
            + sum_value(grp, "final energy|clothes washer|electricity")
            + sum_value(grp, "final energy|clothes dryer|electricity")
            + sum_value(grp, "final energy|dish washer|electricity")
            + sum_value(grp, "final energy|cooking|electricity")
        )

        elec_cats = {
            "Electricity - Refrigeration and freezers": e_rf,
            "Electricity - Lighting": e_lighting,
            "Electricity - Space cooling": e_space_cooling,
            "Electricity - Space heating": e_space_heating,
            "Electricity - Water heating": e_water_heating,
            "Electricity - Other": e_other,
        }
        for name, pj in elec_cats.items():
            rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Residential", "Category": name, "PJ": pj * r_elec})
            rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Commercial",  "Category": name, "PJ": pj * c_elec})

        # Natural gas end-uses
        ng_sph   = sum_value(grp, "final energy|space heating|natural gas")
        ng_wah   = sum_value(grp, "final energy|water heating|natural gas")
        ng_other = (
            sum_value(grp, "final energy|cooking|natural gas")
            + sum_value(grp, "final energy|clothes dryer|natural gas")
        )
        ng_cats = {
            "Natural Gas - Space heating": ng_sph,
            "Natural Gas - Water heating": ng_wah,
            "Natural Gas - Other": ng_other,
        }
        for name, pj in ng_cats.items():
            rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Residential", "Category": name, "PJ": pj * r_ng})
            rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Commercial",  "Category": name, "PJ": pj * c_ng})

        # Biomass & Other (assign to Residential by default; adjust if desired)
        bio_sph = sum_value(grp, "final energy|space heating|wood")
        other_fossil = (
            sum_value(grp, "final energy|space heating|oil")
            + sum_value(grp, "final energy|space heating|other")
            + sum_value(grp, "final energy|water heating|oil")
            + sum_value(grp, "final energy|water heating|lpg")
        )
        rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Residential", "Category": "Biomass - Space heating", "PJ": bio_sph})
        rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Commercial",  "Category": "Biomass - Space heating", "PJ": 0.0})
        rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Residential", "Category": "Other", "PJ": other_fossil})
        rows.append({"ScenarioLabel": scen, "Year": year, "Sector": "Commercial",  "Category": "Other", "PJ": 0.0})

    out = pd.DataFrame(rows)
    out["EJ"] = out["PJ"] / 1000.0
    return out

# ---------- Plot ----------
ORDER = [
    "Electricity - Refrigeration and freezers",
    "Electricity - Lighting",
    "Electricity - Space cooling",
    "Electricity - Space heating",
    "Electricity - Water heating",
    "Electricity - Other",
    "Natural Gas - Space heating",
    "Natural Gas - Water heating",
    "Natural Gas - Other",
    "Biomass - Space heating",
    "Other",
]

def plot_four_panel(df: pd.DataFrame, out_path: str, region_label: str) -> None:
    df = df.copy()
    df["Category"] = pd.Categorical(df["Category"], categories=ORDER, ordered=True)

    sectors = ["Residential", "Commercial"]
    scenarios = ["Current Policy Scenario", "Net-Zero Scenario"]

    fig, axes = plt.subplots(2, 2, figsize=(12, 7), sharey=True, dpi=150)
    for i, sec in enumerate(sectors):
        for j, scen in enumerate(scenarios):
            ax = axes[i, j]
            part = df[(df["Sector"] == sec) & (df["ScenarioLabel"] == scen)]
            pv = (
                part.pivot_table(index="Year", columns="Category", values="EJ", aggfunc="sum")
                .reindex(columns=ORDER)
                .fillna(0.0)
            )
            years = pv.index.values
            bottom = np.zeros(len(years))
            for col in pv.columns:
                ax.bar(years, pv[col].values, bottom=bottom, width=BAR_WIDTH, label=col)
                bottom += pv[col].values

            ax.set_title(f"{scen} – {sec}")
            ax.set_xlabel("Year")
            if j == 0:
                ax.set_ylabel("Energy Consumption (EJ)")
            ax.grid(axis="y", linestyle=":", linewidth=0.5)
            if len(years):
                ax.set_xlim(years.min() - 4, years.max() + 4)

    # Region title + legend
    fig.suptitle(f"Region: {region_label}", y=0.98, fontsize=11)
    handles, labels = axes[0, 1].get_legend_handles_labels()
    fig.legend(handles, labels, title="Source - End Use", loc="center left", bbox_to_anchor=(1.02, 0.5))
    plt.tight_layout(rect=[0, 0, 0.8, 0.95])
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Buildings energy four-panel plot for a single province or Canada.")
    ap.add_argument("--region", default="CAN", help="Province code/name (e.g., AB) or 'CAN' to aggregate nationally. Also accepts ALL/CANADA.")
    ap.add_argument("--ref_eu", default=END_USE_REF_DEFAULT, help="End-use energy (Current Policy) CSV")
    ap.add_argument("--nz_eu",  default=END_USE_NZ_DEFAULT,  help="End-use energy (Net-Zero) CSV")
    ap.add_argument("--ref_py", default=PYAM_REF_DEFAULT,    help="Optional pyam CSV (Current Policy)")
    ap.add_argument("--nz_py",  default=PYAM_NZ_DEFAULT,     help="Optional pyam CSV (Net-Zero)")
    ap.add_argument("--out",    default=None,                help="Output image filename (auto if not set)")
    args = ap.parse_args()

    region_norm = normalize_region(args.region)

    # Load end-use energy for chosen region
    ref_eu = load_end_use(args.ref_eu, "Current Policy Scenario", region_norm)
    nz_eu  = load_end_use(args.nz_eu,  "Net-Zero Scenario",        region_norm)
    end_use_all = pd.concat([ref_eu, nz_eu], ignore_index=True)

    # Load pyam (optional) for the same region and compute sector shares
    ref_py = load_pyam(args.ref_py, "Current Policy Scenario", region_norm)
    nz_py  = load_pyam(args.nz_py,  "Net-Zero Scenario",        region_norm)
    frames = [x for x in [ref_py, nz_py] if isinstance(x, pd.DataFrame)]
    pyam_all = pd.concat(frames, ignore_index=True) if frames else None
    shares = compute_sector_shares(pyam_all) if pyam_all is not None else None

    # Build and plot
    tbl = build_table(end_use_all, shares)
    out_name = args.out or f"buildings_by_sector_from_end_use_energy_four_panel_{region_norm}.png"
    plot_four_panel(tbl, out_name, region_norm)
    print(f"Saved: {out_name}")

if __name__ == "__main__":
    main()
