# make_industry_energy_by_fuel_region_two_panel.py
# Two-panel stacked bar of *industry* energy by fuel for a chosen region
# (single province by code/name) or Canada aggregate.
#
# Sources: pyam-style CSVs: ref_pyam.csv (Current Policy) and nz_pyam.csv (Net-Zero)
# Variables: Activity|industrial|F_I_* plus electricity
#
# Usage:
#   python make_industry_energy_by_fuel_region_two_panel.py --region CAN
#   python make_industry_energy_by_fuel_region_two_panel.py --region AB
# Optional:
#   --ref ref_pyam.csv --nz nz_pyam.csv --out my_plot.png
#
# Notes:
# - If --region CAN (or ALL/CANADA), the script aggregates across all regions.
# - If a specific region (e.g., AB) is provided, the script filters to that region.
# - Converts PJ -> EJ for display.
#
# Author: updated for regional selection

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

REF_FILE = "ref_pyam.csv"
NZ_FILE  = "nz_pyam.csv"
BAR_WIDTH = 4.0

KEEP_VARS = [
    "Activity|industrial|E_I_ELC",  # Electricity
    "Activity|industrial|F_I_NG",   # Natural gas
    "Activity|industrial|F_I_BIO",  # Biomass
    "Activity|industrial|F_I_H2",   # Hydrogen
    "Activity|industrial|F_I_HFO",  # Residual Fuel Oil
    # Optional extras if present in your data:
    "Activity|industrial|F_I_DSL",  # Diesel
    "Activity|industrial|F_I_GSL",  # Gasoline
    "Activity|industrial|F_I_COL",  # Coal
    "Activity|industrial|F_I_OFSL", # Other Fossil
]
FUEL_MAP = {
    "Activity|industrial|E_I_ELC": "Electricity",
    "Activity|industrial|F_I_NG":  "Natural Gas",
    "Activity|industrial|F_I_BIO": "Biomass",
    "Activity|industrial|F_I_H2":  "Hydrogen",
    "Activity|industrial|F_I_HFO": "Residual Fuel Oil",
    "Activity|industrial|F_I_DSL": "Diesel",
    "Activity|industrial|F_I_GSL": "Gasoline",
    "Activity|industrial|F_I_COL": "Coal",
    "Activity|industrial|F_I_OFSL": "Other Fossil",
}
PANEL_ORDER = ["Current Policy Scenario","Net-Zero Scenario"]
FUEL_ORDER  = ["Hydrogen","Electricity","Biomass","Residual Fuel Oil","Natural Gas",
               "Gasoline","Diesel","Coal","Other Fossil"]

def load_pyam(path: str, scen_label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    year_cols = [c for c in df.columns if str(c).isdigit()]
    long = df.melt(id_vars=["Model","Scenario","Region","Variable","Unit"],
                   value_vars=year_cols, var_name="Year", value_name="PJ")
    long["Year"] = long["Year"].astype(int)
    long["ScenarioLabel"] = scen_label
    return long

def normalize_region(region: str) -> str:
    if region is None:
        return "CAN"
    r = str(region).strip().upper()
    synonyms = {"ALL": "CAN", "CANADA": "CAN", "ALL_CANADA": "CAN"}
    return synonyms.get(r, r)

def aggregate_to_target(df: pd.DataFrame, region: str) -> pd.DataFrame:
    """If region == 'CAN', sum across all provinces to a Canada total.
    Otherwise, filter to a single province code/name (case-insensitive)."""
    region = normalize_region(region)
    if region == "CAN":
        grouped = df.groupby(["ScenarioLabel","Fuel","Year"], as_index=False)["PJ"].sum()
        grouped["RegionLabel"] = "CAN"
        return grouped

    mask = df["Region"].astype(str).str.upper() == region
    sub = df.loc[mask].copy()
    if sub.empty:
        available = ", ".join(sorted(df["Region"].dropna().astype(str).unique()))
        raise ValueError(f"Region '{region}' not found. Available Region values: {available}")
    grouped = sub.groupby(["ScenarioLabel","Fuel","Year"], as_index=False)["PJ"].sum()
    grouped["RegionLabel"] = region
    return grouped

def main():
    ap = argparse.ArgumentParser(description="Industry energy by fuel (two-panel) for a region or Canada total.")
    ap.add_argument("--region", default="CAN", help="Province code/name (e.g., AB) or 'CAN' for national aggregate. Also accepts ALL/CANADA.")
    ap.add_argument("--ref", default=REF_FILE, help="Path to Current Policy pyam CSV (default: ref_pyam.csv)")
    ap.add_argument("--nz",  default=NZ_FILE,  help="Path to Net-Zero pyam CSV (default: nz_pyam.csv)")
    ap.add_argument("--out", default=None,     help="Output image filename (default auto-derived)")
    args = ap.parse_args()

    frames = []
    if Path(args.ref).exists():
        frames.append(load_pyam(args.ref, "Current Policy Scenario"))
    if Path(args.nz).exists():
        frames.append(load_pyam(args.nz, "Net-Zero Scenario"))
    if not frames:
        raise FileNotFoundError("No pyam CSVs found. Provide --ref and/or --nz pointing to valid files.")

    df = pd.concat(frames, ignore_index=True)
    # Keep only industrial fuel variables of interest
    df = df[df["Variable"].isin(KEEP_VARS)].copy()
    df["Fuel"] = df["Variable"].map(FUEL_MAP)

    # Build either province-only or Canada aggregate
    target_region = normalize_region(args.region)
    grouped = aggregate_to_target(df, target_region)

    # PJ -> EJ
    grouped["EJ"] = grouped["PJ"] / 1000.0

    # Only include fuels present; keep order as in FUEL_ORDER
    fuels_present = [f for f in FUEL_ORDER if f in grouped["Fuel"].unique()]
    grouped["Fuel"] = pd.Categorical(grouped["Fuel"], categories=fuels_present, ordered=True)

    # Plot
    fig, axes = plt.subplots(1, 2, figsize=(11,4), sharey=True, dpi=150)
    for ax, scen in zip(axes, PANEL_ORDER):
        part = grouped[grouped["ScenarioLabel"]==scen]
        pv = (part.pivot_table(index="Year", columns="Fuel", values="EJ", aggfunc="sum")
                    .reindex(columns=fuels_present).fillna(0.0))
        years = pv.index.values
        bottom = np.zeros(len(years))
        for col in pv.columns:
            ax.bar(years, pv[col].values, bottom=bottom, width=BAR_WIDTH, label=col)
            bottom += pv[col].values
        ax.set_title(scen)
        ax.set_xlabel("Year")
        if ax is axes[0]:
            ax.set_ylabel("Energy Consumption (EJ)")
        ax.grid(axis="y", linestyle=":", linewidth=0.5)
        if len(years):
            ax.set_xlim(years.min()-4, years.max()+4)

    # Title & legend
    region_label = grouped["RegionLabel"].iloc[0] if len(grouped) else target_region
    fig.suptitle(f"Region: {region_label}", y=0.98, fontsize=11)

    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, title="Fuel", loc="center left", bbox_to_anchor=(1.02, 0.5))
    plt.tight_layout(rect=[0,0,0.85,0.94])

    # Output
    out_file = args.out or f"industry_energy_by_fuel_two_panel_{region_label}.png"
    plt.savefig(out_file, bbox_inches="tight")
    plt.close()
    print(f"Saved: {out_file}")

if __name__ == "__main__":
    main()
