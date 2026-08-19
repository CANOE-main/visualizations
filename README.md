# CANOE Visualizations

Preliminary visualization tools for exploring and communicating outputs from the CANOE energy system model.

> **Development status: Preliminary / Experimental**
>
> The visualizations in this repository are early versions and are expected to change substantially as the visualization framework is developed. They are intended to demonstrate possible approaches to presenting CANOE results rather than define the final visualization style, data pipeline, or reporting framework.

## Overview

This repository contains a collection of Python scripts for converting CANOE model outputs into publication- and presentation-oriented figures.

The current visualizations focus on comparing energy-system outcomes between scenarios, particularly:

* **Current Policy**
* **Net-Zero**

The initial graphs cover emissions, electricity capacity, primary energy consumption, sectoral electricity consumption, transportation fuels, building energy use, and industrial fuels.

The longer-term goal is to develop these preliminary examples into a more consistent and reusable CANOE visualization framework.

## Current Visualizations

### Graph 1 — Emissions by Source

Produces a two-panel stacked-area visualization comparing net emissions by source between the Current Policy and Net-Zero scenarios.

Current source categories include:

* Electricity
* Industrial
* Transportation
* Commercial
* Residential
* Agriculture

**Current note:** the region is presently configured directly in the script and is set to Prince Edward Island.

Typical output:

```text
net_emissions_by_source.png
```

---

### Graph 2 — Electricity Capacity by Source

Shows installed electricity generation and storage capacity by technology/source for each scenario.

Current categories include technologies such as:

* Wind
* Solar
* Hydro
* Natural gas
* Nuclear
* Biomass
* Coal
* Hydrogen
* Battery storage
* Pumped hydro

Outputs can be generated separately for each scenario and optionally combined side-by-side.

Example outputs:

```text
capacity_by_source_current_policy_scenario.png
capacity_by_source_net-zero_scenario.png
capacity_by_source_combined.png
```

**Current note:** the region is presently configured directly in the script and is set to Prince Edward Island.

---

### Graph 3 — Primary Energy Consumption

Produces side-by-side stacked-area plots comparing estimated primary energy consumption under the Current Policy and Net-Zero scenarios.

The graph combines electricity-generation information with final fuel consumption to estimate primary energy by source.

Example categories include:

* Wind
* Solar
* Biomass
* Other renewables
* Nuclear
* Natural gas
* Petroleum
* Coal

Output:

```text
primary_energy_two_panel.png
```

**Important:** thermal-generation efficiencies are currently defined within the script. These assumptions are preliminary and should be reviewed before using this visualization for formal analysis.

**Current note:** the region is presently configured directly in the script and is set to Prince Edward Island.

---

### Graph 4 — Electricity Consumption by Sector

Compares electricity consumption by sector between the Current Policy and Net-Zero scenarios.

Current sectors include:

* Commercial
* Residential
* Industrial
* Transportation
* Agriculture

The script supports either:

* an individual region/province; or
* a Canada-wide aggregate.

For example:

```bash
cd "Graph 4"

python script.py --region AB
```

or:

```bash
python script.py --region CAN
```

Electricity consumption is displayed in TWh.

---

### Graph 5 — Transportation Energy by Fuel

Shows transportation energy consumption by fuel under the Current Policy and Net-Zero scenarios.

Current fuel categories include:

* Electricity
* Diesel
* Gasoline
* Ethanol
* Biodiesel
* Jet fuel
* Natural-gas-based fuels
* Other fossil fuels

The script supports regional or Canada-wide aggregation.

Example:

```bash
cd "Graph 5"

python script.py --region AB
```

Energy consumption is converted from PJ to EJ for display.

Some additional fuels, including hydrogen and synthetic fuels, are already identified as potential additions and will be incorporated as the underlying CANOE outputs evolve.

---

### Graph 6 — Residential and Commercial Building Energy

Provides a four-panel comparison of building energy consumption:

|                 | Current Policy | Net-Zero |
| --------------- | -------------- | -------- |
| **Residential** | ✓              | ✓        |
| **Commercial**  | ✓              | ✓        |

Current end-use categories include electricity and natural-gas consumption for activities such as:

* Space heating
* Water heating
* Space cooling
* Lighting
* Refrigeration and freezers
* Other electrical loads
* Other building fuels

The visualization can use additional PYAM-formatted output to estimate the Residential/Commercial split for electricity and natural gas.

If this information is unavailable, the current preliminary implementation falls back to a 50/50 split.

Example:

```bash
cd "Graph 6"

python script.py --region AB
```

This allocation method is temporary and is an area identified for improvement.

---

### Graph 7 — Industrial Energy by Fuel

Compares industrial energy consumption by fuel between the Current Policy and Net-Zero scenarios.

Current fuel categories include:

* Electricity
* Natural gas
* Biomass
* Hydrogen
* Residual fuel oil
* Diesel
* Gasoline
* Coal
* Other fossil fuels

The visualization can be produced for either an individual region or Canada as a whole.

Example:

```bash
cd "Graph 7"

python script.py --region AB
```

---

## Repository Structure

```text
visualizations/
│
├── Graph 1/
│   ├── emissions.csv
│   ├── emissions_ref.csv
│   └── script.py
│
├── Graph 2/
│   ├── capacity.csv
│   ├── capacity_ref.csv
│   └── script.py
│
├── Graph 3/
│   ├── generation.csv
│   ├── generation_ref.csv
│   ├── end_use_energy.csv
│   ├── end_use_energy_ref.csv
│   └── script.py
│
├── Graph 4/
│   ├── nz_pyam.csv
│   ├── ref_pyam.csv
│   └── script.py
│
├── Graph 5/
│   ├── nz_pyam.csv
│   ├── ref_pyam.csv
│   └── script.py
│
├── Graph 6/
│   ├── end_use_energy.csv
│   ├── end_use_energy_ref.csv
│   └── script.py
│
├── Graph 7/
│   ├── nz_pyam.csv
│   ├── ref_pyam.csv
│   └── script.py
│
├── canoe_visualization.ipynb
└── run_all.py
```

The CSV files currently included in the graph directories provide the data used by the preliminary examples.

As the project develops, input data handling is expected to become more centralized so that the same CANOE output files do not need to be duplicated between visualization folders.

## Installation

Clone the repository:

```bash
git clone https://github.com/david-turnbull/visualizations.git
cd visualizations
```

Creating a virtual environment is recommended:

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

or on macOS/Linux:

```bash
source .venv/bin/activate
```

Install the main packages currently used by the visualization scripts:

```bash
pip install pandas numpy matplotlib pillow jupyter
```

A formal `requirements.txt` or package configuration should be added as the project matures.

## Running a Single Visualization

Each graph can be executed independently.

For example:

```bash
cd "Graph 2"
python script.py
```

Scripts supporting regional selection can be run with:

```bash
python script.py --region AB
```

or:

```bash
python script.py --region CAN
```

Some scripts also support custom input and output paths. Run:

```bash
python script.py --help
```

to see the arguments available for that visualization.

## Running Multiple Visualizations

The repository includes `run_all.py`, which can execute visualization scripts concurrently.

To run all scripts matching the current folder structure:

```bash
python run_all.py --glob "Graph */script.py"
```

To limit the number of scripts running simultaneously:

```bash
python run_all.py --glob "Graph */script.py" --max-procs 3
```

Individual scripts can also be specified:

```bash
python run_all.py "Graph 1/script.py" "Graph 2/script.py"
```

A specific Python interpreter or virtual environment can be supplied:

```bash
python run_all.py --glob "Graph */script.py" --python .venv/Scripts/python.exe
```

Logs are written to:

```text
logs/
```

with a separate log for each visualization script.

### Current `run_all.py` limitation

`run_all.py` currently launches each visualization using its default arguments.

This is important because the repository does not yet use a single consistent regional configuration:

* Graphs 1–3 currently contain a region configured directly in the script.
* Graphs 4–7 support regional command-line arguments and generally default to Canada.

A future version should provide a common configuration such as:

```bash
python run_all.py --region AB
```

and propagate that configuration to every applicable visualization.

## Input Data

The scripts currently use two main forms of CANOE output.

### Long-format output

Some files use a structure similar to:

```text
model
scenario
region
variable
unit
time
value
```

Examples include:

```text
emissions.csv
capacity.csv
generation.csv
end_use_energy.csv
```

### PYAM-style wide output

Other visualizations use output with years represented as columns, for example:

```text
Model
Scenario
Region
Variable
Unit
2025
2030
2035
...
```

These files are typically named:

```text
nz_pyam.csv
ref_pyam.csv
```

The scripts reshape these tables internally before plotting.

## Scenario Naming

The preliminary scripts generally interpret:

```text
reference
```

as:

```text
Current Policy Scenario
```

and:

```text
nz
```

as:

```text
Net-Zero Scenario
```

This mapping is currently defined within individual scripts.

A future version should centralize scenario definitions and allow arbitrary CANOE scenarios to be compared.

## Current Limitations

This repository is intentionally preliminary. Several areas require further development before the visualization framework should be considered stable.

Current limitations include:

* inconsistent regional configuration between graphs;
* some regions and assumptions are hard-coded;
* visualization configuration is repeated between scripts;
* fuel and technology mappings are currently defined manually;
* some calculations use preliminary assumptions;
* data files are duplicated between graph directories;
* limited validation of input files;
* limited handling of missing or unexpected variables;
* no centralized configuration;
* no automated test suite;
* no formal Python package structure;
* no standardized visual theme across all figures;
* no automated connection to CANOE model runs;
* some figures contain logic that should eventually be separated from plotting logic;
* output file naming and directory management are not yet standardized.

The current graphs should therefore be treated as **examples and prototypes**, rather than authoritative final reporting outputs.

## Planned Improvements

Potential next steps include:

### 1. Standardize regional selection

Allow every visualization to use the same interface:

```bash
--region AB
--region ON
--region CAN
```

and remove regions hard-coded within individual scripts.

### 2. Centralize configuration

Move common settings into shared configuration, including:

* scenarios
* regions
* units
* technology mappings
* fuel mappings
* colours
* labels
* output paths

### 3. Separate data processing from plotting

Refactor the project toward reusable components such as:

```text
visualizations/
├── data/
├── processing/
├── plots/
├── config/
└── outputs/
```

This would allow multiple visualizations to use the same processed CANOE results.

### 4. Standardize visual design

Develop a common CANOE visualization style covering:

* typography;
* scenario presentation;
* technology and fuel colours;
* legends;
* figure dimensions;
* units;
* titles;
* accessibility;
* export resolution.

### 5. Improve data validation

Add checks for:

* missing variables;
* unexpected units;
* missing scenarios;
* missing regions;
* duplicate values;
* incomplete time series.

### 6. Connect directly to CANOE outputs

Reduce the need to manually copy CSV files into individual graph directories.

Ideally the visualization layer will eventually accept a CANOE results directory or database and generate the required figures automatically.

### 7. Add a visualization CLI

A future interface could resemble:

```bash
canoe-viz emissions --region AB
canoe-viz capacity --region ON
canoe-viz transportation --region CAN
```

or:

```bash
canoe-viz all --region AB
```

### 8. Expand visualization coverage

Additional visualizations may include:

* electricity generation;
* technology deployment;
* capacity additions and retirements;
* fuel production and consumption;
* hydrogen production and use;
* interprovincial electricity trade;
* emissions by sector and technology;
* costs and investment;
* demand evolution;
* technology-level comparisons;
* regional comparisons;
* scenario differences;
* national energy-flow visualizations.

## Development Philosophy

The purpose of the current repository is to establish **what information should be communicated and how CANOE results can be made easier to understand** before committing to a final visualization architecture.

For this reason, the repository currently prioritizes experimentation and rapid iteration over package maturity.

Visualizations may therefore be:

* redesigned;
* replaced;
* consolidated;
* split into multiple figures;
* connected to different data sources; or
* moved into a more formal visualization package.

Feedback on clarity, usefulness, and interpretation of the figures is particularly valuable during this stage.

## Jupyter Notebook

The repository also contains:

```text
canoe_visualization.ipynb
```

This notebook can be used for exploratory visualization development and testing.

The standalone `Graph N/script.py` files are useful for testing visualizations as reproducible scripts, while the notebook provides a more interactive environment for experimentation.

## Contributing

This project is currently under active development.

Contributions, suggestions, and feedback are welcome, particularly around:

* useful CANOE result visualizations;
* consistent presentation across sectors;
* regional comparison methods;
* scenario comparison methods;
* accessibility and readability;
* reusable plotting architecture;
* automated data ingestion;
* testing and validation.

Because the visualization framework is still evolving, larger structural changes should ideally be discussed before implementation.

## Disclaimer

These visualizations are preliminary and may contain assumptions, mappings, transformations, or presentation choices that are still being reviewed.

They should not be treated as final or authoritative CANOE outputs without checking the underlying model results and visualization methodology.

The figures are intended to support development of the CANOE visualization framework and will continue to be refined as the model, data pipelines, and reporting requirements evolve.
