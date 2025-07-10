from pathlib import Path
import math
import femm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


class FEMMModel:
    """Handles loading, translating, and solving a FEMM model."""

    def __init__(self, model_path: Path, amplitude: float, period: float, coil_length: float):
        if not model_path.exists():
            raise FileNotFoundError(f"File not found: {model_path}")

        self.model_path = model_path
        self.output_path = Path("SimOutput.fem")
        self.position = 0.0

        self.amplitude = amplitude
        self.period = period
        self.coil_length = coil_length
        self.currents: dict[str, float] = {}

        femm.openfemm(1)
        femm.opendocument(str(self.model_path))
        femm.mi_probdef(0, "millimeters", "axi")

    def mesh_and_solve(self):
        """Save, mesh, and run the simulation."""
        femm.mi_saveas(str(self.output_path))
        femm.mi_createmesh()
        femm.mi_analyze()

    def compute_current(self, pos: float, phase: float = 0.0) -> float:
        """Compute coil currents from position and model parameters"""
        angle = (2 * math.pi * pos / self.period +
                 phase + 2 * math.pi * self.coil_length / self.period)
        return self.amplitude * math.sin(angle)

    def translate_and_set_currents(self, delta: float):
        """Translate the model and update coil currents."""
        femm.mi_clearselected()
        femm.mi_seteditmode("group")

        for group_id in range(1, 5):
            femm.mi_selectgroup(group_id)

        femm.mi_movetranslate(0, delta)
        self.position += delta

        self.currents = {
            "CoilA": self.compute_current(self.position, 0),
            "CoilB": self.compute_current(self.position, 2 * math.pi / 3),
            "CoilC": self.compute_current(self.position, -2 * math.pi / 3),
        }

        for coil, current in self.currents.items():
            femm.mi_setcurrent(coil, current)


class SimulationResult:
    """Stores and extracts forces and currents from a solved FEMM model."""

    def __init__(self, femm_model: FEMMModel):
        self.position = femm_model.position
        self.results = {
            "Position": self.position,
            "Current": femm_model.currents.copy(),
        }
        self._compute_forces()

    def _compute_forces(self):
        """Extracts forces from FEMM model."""
        femm.mi_loadsolution()
        femm.mo_smooth("off")
        femm.mo_hidecontourplot()

        self.results["Force"] = {}
        for i, coil in enumerate(["CoilA", "CoilB", "CoilC"], start=1):
            femm.mo_clearblock()
            femm.mo_groupselectblock(i)
            force = femm.mo_blockintegral(19)
            self.results["Force"][coil] = force

        # Total force
        femm.mo_clearblock()
        for group in [1, 2, 3]:
            femm.mo_groupselectblock(group)
        total_force = femm.mo_blockintegral(19)
        self.results["Force"]["Sum"] = total_force
        femm.mo_clearblock()


def run_simulation(model: FEMMModel, start: float, end: float, step: float) -> list:
    """Run the simulation over a range of positions and collect results."""
    results = []

    model.translate_and_set_currents(start)
    model.mesh_and_solve()
    results.append(SimulationResult(model).results)

    for _ in np.arange(start, end, step):
        model.translate_and_set_currents(step)
        model.mesh_and_solve()
        results.append(SimulationResult(model).results)
        print(f"Simulated position: {model.position:.2f}")

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
                color=color_list[i]
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
                color=color_list[i]
                )
    ax2.set_ylabel("Current (A)")
    ax2.tick_params("y")
    ax2.legend(loc="upper right")

    plt.tight_layout()
    plt.savefig("Results_Force_Currents.png")
    plt.show()


if __name__ == "__main__":
    src_path = Path.cwd() / "SimuFile.fem"
    print(f"FEM source file: {src_path}")

    # Simulation parameters
    START_POS = -20
    END_POS = 20
    STEP_SIZE = 1

    # Model parameters
    PEAK_CURRENT = 3.0
    PERIOD = 40.0  # length of x2 magnets
    COIL_LENGTH = 6.8

    fem_model = FEMMModel(
        model_path=src_path,
        amplitude=PEAK_CURRENT,
        period=PERIOD,
        coil_length=COIL_LENGTH
    )

    simulation_data = run_simulation(fem_model, START_POS, END_POS, STEP_SIZE)
    df = pd.json_normalize(simulation_data).set_index("Position")
    df.to_csv("SimulationResults.csv")

    plot_results(df)
