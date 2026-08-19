# make_elec_by_sector_from_pyam_agri_region.py
# System-wide electricity consumption by sector (Commercial, Residential, Industrial, Transport, Agriculture).
# Adds --region so you can plot for one province (e.g., AB) or aggregate to all of Canada (CAN).
#
# Usage examples:
#   python make_elec_by_sector_from_pyam_agri_region.py --region CAN
#   python make_elec_by_sector_from_pyam_agri_region.py --region AB
# Optional:
#   --nz nz_pyam.csv --ref ref_pyam.csv --out my_plot.png

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

NZ_FILE  = "nz_pyam.csv"
REF_FILE = "ref_pyam.csv"
BAR_WIDTH = 3.0

# Electric end-use mapping
VARS = {
    "Commercial":   "Activity|commercial|E_C_ELC",
    "Residential":  "Activity|residential|E_R_ELC",
    "Industrial":   "Activity|industrial|E_I_ELC",
    "Transport":    "Activity|transportation|E_T_ELC",
    "Agriculture":  "Activity|agriculture|E_A_ELC",
}

PANEL_ORDER  = ["Current Policy Scenario", "Net-Zero Scenario"]
SECTOR_ORDER = ["Commercial","Residential","Industrial","Transport","Agriculture"]

def load_pyam(path: str, scen_label: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    year_cols = [c for c in df.columns if str(c).isdigit()]
    long = df.melt(
        id_vars=["Model","Scenario","Region","Variable","Unit"],
        value_vars=year_cols,
        var_name="Year",
        value_name="PJ",
    )
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
        return df.groupby(["ScenarioLabel","Variable","Year"], as_index=False)["PJ"].sum()

    # Single province
    mask = df["Region"].str.upper() == region
    sub = df.loc[mask].copy()
    if sub.empty:
        available = ", ".join(sorted(df["Region"].dropna().astype(str).unique()))
        raise ValueError(
            f"Region '{region}' not found in file(s). "
            f"Available Region values: {available}"
        )
    return sub.groupby(["ScenarioLabel","Variable","Year"], as_index=False)["PJ"].sum()

def build_sector_table(df_grouped: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for scen, d1 in df_grouped.groupby("ScenarioLabel"):
        for year, d2 in d1.groupby("Year"):
            for sector, var in VARS.items():
                val = d2.loc[d2["Variable"] == var, "PJ"].sum()
                rows.append({"ScenarioLabel": scen, "Year": year, "Sector": sector, "PJ": val})
    out = pd.DataFrame(rows)
    out["TWh"] = out["PJ"] / 3.6
    return out

def plot_two_panel(agg: pd.DataFrame, out_path: str, region_label: str):
    agg = agg.copy()
    agg["Sector"] = pd.Categorical(agg["Sector"], categories=SECTOR_ORDER, ordered=True)
    fig, axes = plt.subplots(1, 2, figsize=(11,4), sharey=True, dpi=150)

    for ax, scen in zip(axes, PANEL_ORDER):
        part = agg[agg["ScenarioLabel"] == scen]
        pv = (
            part.pivot_table(index="Year", columns="Sector", values="TWh", aggfunc="sum")
                .reindex(columns=SECTOR_ORDER).fillna(0.0)
        )
        years = pv.index.values
        bottom = np.zeros(len(years))
        for col in pv.columns:
            ax.bar(years, pv[col].values, bottom=bottom, width=BAR_WIDTH, label=col)
            bottom += pv[col].values
        ax.set_title(scen)
        ax.set_xlabel("Year")
        if ax is axes[0]:
            ax.set_ylabel("Electricity consumption (TWh)")
        ax.grid(axis="y", linestyle=":", linewidth=0.5)
        if len(years):
            ax.set_xlim(years.min()-4, years.max()+4)

    # Figure-level title indicating the region
    fig.suptitle(f"Region: {region_label}", y=0.98, fontsize=11)

    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, title="Sector", loc="center left", bbox_to_anchor=(1.02, 0.5))
    plt.tight_layout(rect=[0,0,0.85,0.94])
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def main():
    ap = argparse.ArgumentParser(description="Plot electricity by sector for a single province or Canada total.")
    ap.add_argument("--region", default="CAN", help="Province code/name (e.g., AB) or 'CAN' to aggregate to Canada. Case-insensitive. Also accepts 'ALL'/'CANADA'.")
    ap.add_argument("--nz", default=NZ_FILE, help="Path to Net-Zero pyam CSV (default: nz_pyam.csv)")
    ap.add_argument("--ref", default=REF_FILE, help="Path to Current Policy pyam CSV (default: ref_pyam.csv)")
    ap.add_argument("--out", default=None, help="Output image filename (default auto-derived)")
    args = ap.parse_args()

    frames = []
    if Path(args.ref).exists():
        frames.append(load_pyam(args.ref, "Current Policy Scenario"))
    if Path(args.nz).exists():
        frames.append(load_pyam(args.nz, "Net-Zero Scenario"))

    if not frames:
        raise FileNotFoundError("No pyam CSVs found. Looked for: "
                                f"{Path(args.ref).resolve()} and {Path(args.nz).resolve()}")

    data = pd.concat(frames, ignore_index=True)

    # Prepare to-region (province or CAN aggregate)
    region_code = normalize_region(args.region)
    grouped = aggregate_to_target(data, region_code)

    agg = build_sector_table(grouped)

    # Default output filename
    out_path = args.out or f"elec_by_sector_pyam_agri_two_panel_{region_code}.png"
    plot_two_panel(agg, out_path, region_code)
    print(f"Saved: {out_path}")

if __name__ == "__main__":
    main()
