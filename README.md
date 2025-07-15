# FEMM Linear Motor Simulations

**Work in progress.**

This project provides a modular Python workflow to automate the simulation of tubular linear motors using [FEMM](http://www.femm.info/wiki/HomePage) (Finite Element Method Magnetics).

Motor design from [cmore839/DIY-Linear-Motor](https://github.com/cmore839/DIY-Linear-Motor).

## Features

- **Parametric model generation** from a YAML configuration file
- **Automated simulation** of force and current for multiple positions
- **Results export** to CSV and PNG plots
- **Output management**: all results are saved in the `out/` directory

## Project Structure

```text
FEMM_linear_motor_simulations/
├── coil.py                # Coil data class
├── create_model.py        # Model builder (geometry, circuits, etc.)
├── femm_model.py          # FEMMModel: handles FEMM file operations
├── magnet.py              # Magnet data class
├── Parameters.yml         # Main configuration file (edit this for your motor)
├── README.md              # This file
├── simulation_result.py   # SimulationResult: extracts forces/currents
├── simulate.py            # Main script to run simulations
├── out/                   # All simulation outputs (FEM, CSV, plots)
└── ...
```

## Quick Start

1. **Edit your parameters** in `Parameters.yml` (see example in the file).
2. **Run the main script**:

   ```sh
   python simulate.py
   ```

   This will:
   - Generate the FEMM model from your parameters
   - Run the simulation for all positions
   - Save results in `out/SimulationResults.csv` and plot in `out/Results_Force_Currents.png`

3. **View your results** in the displayed plot and `out/` directory.

## Requirements

- Windows (FEMM is Windows-only)
- Python 3.8+
- FEMM (installed and accessible via Python)
- Python packages: `numpy`, `pandas`, `matplotlib`, `pyyaml`, `pyfemm`

Install dependencies:

```sh
pip install numpy pandas matplotlib pyyaml pyfemm
```

## Customization

- Change simulation parameters (positions, steps, etc.) in `simulate.py`.
- Adjust geometry/materials/current in `Parameters.yml`.
- All output files are written to `out/` (auto-created if missing).

## Tips

- To run multiple simulations in parallel, use several Python processes (one per position or range), each with its own output directory.
- The `.gitignore` is set up to ignore all outputs, and typical Python/VSCode files.

## License

MIT License

---
*Project by Julien (JuPrgn).*
