from pathlib import Path
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from create_model import CreateModel
from femm_model import FEMMModel
from simulation_result import SimulationResult


def run_simulation(femm_model: FEMMModel, start: float, end: float, step: float) -> list:
    """Run the simulation over a range of positions and collect results."""
    results = []

    femm_model.translate_and_set_currents(start)
    femm_model.mesh_and_solve()
    results.append(SimulationResult(femm_model).results)

    for _ in np.arange(start, end, step):
        femm_model.translate_and_set_currents(step)
        femm_model.mesh_and_solve()
        results.append(SimulationResult(femm_model).results)
        print(f"Simulated position: {femm_model.offset_pos:.2f}")

    return results


def plot_results(df_result: pd.DataFrame):
    """Plot force and current curves from simulation results."""
    _, ax1 = plt.subplots(figsize=(10, 6))
    color_list = ["tab:blue", "tab:orange", "tab:green", "tab:red"]

    # Plot forces
    for i, coil in enumerate(["CoilA", "CoilB", "CoilC", "Sum"]):
        col = f"Force.{coil}"
        if col in df_result.columns:
            ax1.plot(
                df_result.index,
                df_result[col],
                "o-",
                label=f"Force {coil}",
                color=color_list[i],
            )
    ax1.set_xlabel("Position (mm)")
    ax1.set_ylabel("Force (N)")
    ax1.grid()
    ax1.legend(loc="upper left")

    # Plot currents
    ax2 = ax1.twinx()
    for i, coil in enumerate(["CoilA", "CoilB", "CoilC"]):
        col = f"Current.{coil}"
        if col in df_result.columns:
            ax2.plot(
                df_result.index,
                df_result[col],
                "--",
                label=f"Current {coil}",
                color=color_list[i],
            )
    ax2.set_ylabel("Current (A)")
    ax2.tick_params("y")
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(out_dir / "Results_Force_Currents.png")
    plt.show()


if __name__ == "__main__":

    # Select if you want to "generate" a FEMM model or "load" an existing
    MODE = "generate"
    # MODE = "load"

    # Simulation parameters
    START_POS = -20  # in mm
    END_POS = 20
    STEP_SIZE = 1

    # Model parameters automatically updated from Yaml if "generate" or hardcoded here for "load"
    PEAK_CURRENT = 3.0  # in A
    POLE_LENGTH = 40.0  # Distance between two identical magnetic poles (N to N or S to S)
    COIL_PITCH = 6.8  # in mm

    if MODE == "generate":
        # Create a model from YAML parameters -> output SimGenerated.fem
        model_param_path = Path.cwd() / "Parameters.yml"
        # Check file exists
        if not model_param_path.exists():
            print(f"Error: YAML file not found: {model_param_path}")
            sys.exit(1)
        print(f"Load parameters from: {model_param_path}")
        try:
            model = CreateModel(model_param_path)
            model.build()
            print("Model successfully generated.")
            fem_path = Path("SimGenerated.fem")
            PEAK_CURRENT = model.coil.current_peak
            POLE_LENGTH = model.magnet.pitch * 2
            COIL_PITCH = model.coil.pitch
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif MODE == "load":
        # Load an existing model
        fem_path = Path.cwd() / "SimuFile.fem"

    else:
        print(f"Unknown mode: {MODE}. Please set MODE to 'generate' or 'load'.")
        sys.exit(1)

    # Check file exists
    if not fem_path.exists():
        print(f"Error: FEM file not found: {fem_path}")
        sys.exit(1)

    try:
        print(f"Loading FEM model from: {fem_path}")
        fem_model = FEMMModel(
            model_path=fem_path,
            peak_current=PEAK_CURRENT,
            pole_length=POLE_LENGTH,
            coil_pitch=COIL_PITCH,
        )
    except Exception as e:
        print(f"Simulation error: {e}")
        sys.exit(1)

    # Make "out" dir if not exists
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)

    simulation_data = run_simulation(fem_model, START_POS, END_POS, STEP_SIZE)
    df = pd.json_normalize(simulation_data).set_index("Position")
    df.to_csv(out_dir / "SimulationResults.csv")
    plot_results(df)
    print("Simulation completed successfully. Results saved in SimulationResults.csv")
