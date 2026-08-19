# make_capacity_plots.py
# Stacked bars of electric capacity by source for each scenario.

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from PIL import Image

# ---------- Configure if needed ----------
INPUTS = [
    "capacity.csv",           # can be NZ or Reference
    "capacity_ref.csv",       # optional second file if you have it
]
REGION = "prince edward island"
UNIT = "GW"

SCENARIO_LABELS = {
    "reference": "Current Policy Scenario",
    "nz": "Net-Zero Scenario",
}
# Order (bottom→top) for stacked bars
STACK_ORDER = [
    "Hydrogen", "Coal", "Natural Gas", "Nuclear", "Biomass",
    "Geothermal", "Hydro", "Solar", "Wind", "Pumped Hydro", "Battery",
]
# Map plotting categories to variable prefixes to sum
CATEGORY_MAP = {
    "Battery":      ["capacity|electricity|storage|battery storage"],
    "Pumped Hydro": ["capacity|electricity|storage|pumped hydro"],
    "Wind":         ["capacity|electricity|renewables|wind onshore", "capacity|electricity|renewables|wind"],
    "Solar":        ["capacity|electricity|renewables|solar PV", "capacity|electricity|renewables|solar"],
    "Hydro":        ["capacity|electricity|hydro",
                     "capacity|electricity|hydro|reservoir",
                     "capacity|electricity|hydro|run of river"],
    "Geothermal":   ["capacity|electricity|geothermal"],
    "Biomass":      ["capacity|electricity|bioenergy|biomass",
                     "capacity|electricity|bioenergy|biogas",
                     "capacity|electricity|bioenergy"],
    "Nuclear":      ["capacity|electricity|nuclear", "capacity|electricity|nuclear|candu"],
    "Natural Gas":  ["capacity|electricity|natural gas",
                     "capacity|electricity|natural gas|combined cycle",
                     "capacity|electricity|natural gas|combustion turbine",
                     "capacity|electricity|natural gas|cogeneration",
                     "capacity|electricity|natural gas|combined cycle ccs"],
    "Coal":         ["capacity|electricity|coal",
                     "capacity|electricity|coal|coal",
                     "capacity|electricity|coal|ccs"],
    "Hydrogen":     ["capacity|electricity|hydrogen"],  # included if present
}

# ---------- Load & prepare ----------
def load_capacity(paths: list[str | Path]) -> pd.DataFrame:
    frames = []
    for p in paths:
        if Path(p).exists():
            frames.append(pd.read_csv(p))
    if not frames:
        raise FileNotFoundError("No capacity CSVs found.")
    df = pd.concat(frames, ignore_index=True)
    df = df[(df["region"].str.lower() == REGION.lower()) & (df["unit"] == UNIT)].copy()
    return df

def collapse_categories(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (scn, year), grp in df.groupby(["scenario", "time"]):
        for cat, prefixes in CATEGORY_MAP.items():
            sub = grp[grp["variable"].apply(lambda v: any(v.startswith(p) for p in prefixes))]
            val = sub["value"].sum() if not sub.empty else 0.0
            rows.append({"Scenario": scn, "Year": int(year), "Category": cat, "Value": val})
    out = pd.DataFrame(rows)
    # drop categories that sum to zero across all years
    keep = out.groupby("Category")["Value"].sum()
    out = out[out["Category"].isin(keep[keep > 0].index)].copy()
    # pretty labels
    out["ScenarioLabel"] = out["Scenario"].map(lambda s: SCENARIO_LABELS.get(s.lower(), s.title()))
    return out
BAR_WIDTH = 4.0 
# ---------- Plot (one figure per scenario; no subplots) ----------
def plot_one_scenario(frame: pd.DataFrame, label: str, out_path: str):
    pv = (frame.pivot_table(index="Year", columns="Category", values="Value", aggfunc="sum")
                .reindex(columns=[c for c in STACK_ORDER if c in frame["Category"].unique()])
                .fillna(0.0))
    years = pv.index.values
    bottom = np.zeros(len(years))

    plt.figure(figsize=(6, 4), dpi=150)  # one chart per figure
    for cat in pv.columns:
        plt.bar(years, pv[cat].values, bottom=bottom, label=cat, width=BAR_WIDTH)
        bottom += pv[cat].values

    plt.title(label)
    plt.xlabel("Year")
    plt.ylabel("Capacity (GW)")
    plt.grid(axis="y", linestyle=":", linewidth=0.5)
    plt.legend(title="Source", loc="center left", bbox_to_anchor=(1.02, 0.5))
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig(out_path, bbox_inches="tight")
    plt.close()

def maybe_stitch(images: list[str], out_path: str):
    if len(images) < 2:
        return
    ims = [Image.open(p) for p in images]
    h = max(im.size[1] for im in ims)
    ims = [im.resize((int(im.size[0] * h / im.size[1]), h)) for im in ims]
    w = sum(im.size[0] for im in ims)
    combo = Image.new("RGB", (w, h), (255, 255, 255))
    x = 0
    for im in ims:
        combo.paste(im, (x, 0))
        x += im.size[0]
    combo.save(out_path)

def main():
    df = load_capacity(INPUTS)
    data = collapse_categories(df)

    out_files = []
    for scen_label, part in data.groupby("ScenarioLabel"):
        out = f"capacity_by_source_{scen_label.replace(' ', '_').lower()}.png"
        plot_one_scenario(part, scen_label, out)
        out_files.append(out)

    # Optional combined side-by-side if both scenarios are present
    if len(out_files) >= 2:
        maybe_stitch(out_files, "capacity_by_source_combined.png")
        print("Saved:", out_files + ["capacity_by_source_combined.png"])
    else:
        print("Saved:", out_files)

if __name__ == "__main__":
    main()
