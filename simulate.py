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


def plot_results(df_result: pd.DataFrame, output_dir: Path):
    """Plot force and current curves from simulation results."""
    _, ax1 = plt.subplots(figsize=(10, 6))
    color_list = ["tab:blue", "tab:orange", "tab:green", "tab:red"]

    # Plot forces
    for i, coil_name in enumerate(["CoilA", "CoilB", "CoilC", "Sum"]):
        col = f"Force.{coil_name}"
        if col in df_result.columns:
            ax1.plot(
                df_result.index,
                df_result[col],
                "o-",
                label=f"Force {coil_name}",
                color=color_list[i],
            )
    ax1.set_xlabel("Position (mm)")
    ax1.set_ylabel("Force (N)")
    ax1.grid()
    ax1.legend(loc="upper left")

    # Plot currents
    ax2 = ax1.twinx()
    for i, coil_name in enumerate(["CoilA", "CoilB", "CoilC"]):
        col = f"Current.{coil_name}"
        if col in df_result.columns:
            ax2.plot(
                df_result.index,
                df_result[col],
                "--",
                label=f"Current {coil_name}",
                color=color_list[i],
            )
    ax2.set_ylabel("Current (A)")
    ax2.tick_params("y")
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig(output_dir / "Results_Force_Currents.png")
    plt.show()


if __name__ == "__main__":
    # Select simulation mode: "generate" to build from YAML, "load" to use an existing FEM file
    simulation_mode = "generate"
    # simulation_mode = "load"

    # Simulation range parameters
    START_POSITION = -20  # in mm
    END_POSITION = 20
    STEP_SIZE = 1

    # Model parameters automatically updated from Yaml if "generate" or hardcoded here for "load"
    PEAK_CURRENT = 3.0  # in A
    POLE_LENGTH = 40.0  # Distance between two identical magnetic poles (N to N or S to S)
    COIL_PITCH = 6.8  # in mm

    if simulation_mode == "generate":
        # Create a model from YAML parameters -> output SimGenerated.fem
        yaml_path = Path.cwd() / "Parameters.yml"
        if not yaml_path.exists():
            print(f"Error: YAML file not found: {yaml_path}")
            sys.exit(1)
        print(f"Load parameters from: {yaml_path}")
        try:
            model_builder = CreateModel(yaml_path)
            model_builder.build()
            print("Model successfully generated.")
            fem_file_path = Path("SimGenerated.fem")
            PEAK_CURRENT = model_builder.coil_params.current_peak
            POLE_LENGTH = model_builder.magnet_params.pitch * 2
            COIL_PITCH = model_builder.coil_params.pitch
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif simulation_mode == "load":
        # Load an existing model
        fem_file_path = Path.cwd() / "SimuFile.fem"

    else:
        print(f"Unknown mode: {simulation_mode}. Please set simulation_mode to 'generate' or 'load'.")
        sys.exit(1)

    # Check FEM file exists
    if not fem_file_path.exists():
        print(f"Error: FEM file not found: {fem_file_path}")
        sys.exit(1)

    try:
        print(f"Loading FEM model from: {fem_file_path}")
        femm_model = FEMMModel(
            model_path=fem_file_path,
            peak_current=PEAK_CURRENT,
            pole_length=POLE_LENGTH,
            coil_pitch=COIL_PITCH,
        )
    except Exception as e:
        print(f"Simulation error: {e}")
        sys.exit(1)

    # Make "out" dir if not exists
    output_dir = Path("out")
    output_dir.mkdir(exist_ok=True)

    simulation_results = run_simulation(femm_model, START_POSITION, END_POSITION, STEP_SIZE)
    df_results = pd.json_normalize(simulation_results).set_index("Position")
    df_results.to_csv(output_dir / "SimulationResults.csv")
    plot_results(df_results, output_dir)
    print("Simulation completed successfully. Results saved in SimulationResults.csv")
