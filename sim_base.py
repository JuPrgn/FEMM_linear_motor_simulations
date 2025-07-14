from pathlib import Path
import math
import femm
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import yaml
import sys


class Magnet:
    def __init__(self, data: dict):
        self.od = data.get("OD")
        self.length = data.get("Length")
        self.pitch = data.get("Pitch")
        self.material = data.get("Material")
        self.spacer_material = data.get("Spacer_material")
        self.number = data.get("Number")
        self.tube_diameter = data.get("Tube_diameter")
        self.tube_material = data.get("Tube_material")

    def __repr__(self):
        return f"<Magnet OD={self.od}, Length={self.length}, Pitch={self.pitch}>"


class Coil:
    def __init__(self, data: dict):
        self.id = data.get("ID")
        self.od = data.get("OD")
        self.length = data.get("Length")
        self.pitch = data.get("Pitch")
        self.material = data.get("Material")
        self.spacer_material = data.get("Spacer_material")
        self.wire_diameter = data.get("Wire_diameter")
        self.nb_turn = data.get("Nb_turn")
        self.number = data.get("Number")
        self.current_peak = data.get("Current_peak")
        self.vertical_offset = data.get("Vertical_offset")
        self.spool_id = data.get("Spool_ID")
        self.spool_material = data.get("Spool_material")
        self.tube_id = data.get("Tube_ID")
        self.tube_od = data.get("Tube_OD")
        self.tube_material = data.get("Tube_material")

    def __repr__(self):
        return f"<Coil ID={self.id}, OD={self.od}, Wire_diameter={self.wire_diameter}>"


class CreateModel:
    """Handles creating a FEMM model, translating, and solving a FEMM model."""

    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.params = {}
        self.magnet = None
        self.coil = None
        self.exp_factor = 0.5
        self.moving_mass = 0
        self.out_path = Path.cwd() / "SimGenerated.fem"

    def build(self):
        """Build the model from YAML file specified parameters"""
        self.load_model_parameters()
        self.validate_params()

        femm.openfemm(1)
        dict_type_analysis = {
            "Magnetic": 0,
            "Electrostatic": 1,
            "Heat Flow": 2,
            "Current Flow": 3,
        }
        femm.newdocument(dict_type_analysis["Magnetic"])
        femm.mi_probdef(0, "millimeters", "axi")

        self.import_materials_property()
        self.create_circuits()
        self.create_magnets()
        self.create_coils()
        self.create_auto_boundary()
        femm.mi_saveas(str(self.out_path))

    def load_model_parameters(self):
        """Import model parameters from YAML file."""
        try:
            with open(self.model_path, "r", encoding="utf-8") as f:
                self.params = yaml.safe_load(f)
                if not isinstance(self.params, dict):
                    raise ValueError("YAML root must be a dictionary")
        except FileNotFoundError:
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error while reading parameters: {e}")

        self._load_objects()

    def _load_objects(self):
        magnet_data = self.params.get("Magnet", {})
        coil_data = self.params.get("Coil", {})

        self.magnet = Magnet(magnet_data)
        self.coil = Coil(coil_data)

    # TODO
    def validate_params(self):
        """Checks that the yaml file contains necessary keys."""
        if "Coil" not in self.params:
            raise ValueError("Missing required section: 'Coil'")

        # required_coil_keys = ['Wire_diameter']
        # for key in required_coil_keys:
        #     if key not in self.params['Coil']:
        #         raise ValueError(f"Missing 'Coil' parameter: '{key}'")

    def get_param(self, *keys, default=None):
        """Access a nested parameter using a sequence of keys."""
        current = self.params
        for key in keys:
            if not isinstance(current, dict):
                return default
            current = current.get(key, default)
            if current is default:
                break
        return current

    def import_materials_property(self):
        """Add materials to project library."""
        material_names = set()
        found_materials: dict[str, set[str]] = {}

        # Always include "Air"
        material_names.add("Air")

        # Search for materials in parameters
        for section_name, section_data in self.params.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if "material" in key.lower() and isinstance(value, str):
                        found_materials.setdefault(section_name, set()).add(value)
                        material_names.add(value)
        for section, materials in found_materials.items():
            print(f"Found materials in {section}: {', '.join(sorted(materials))}")

        # Add materials to FEMM
        added = []
        failed = []
        for material_name in sorted(material_names):
            try:
                femm.mi_getmaterial(material_name)
                added.append(material_name)
            except Exception as e:
                failed.append((material_name, str(e)))
        # Print added materials
        if added:
            print(f"✔ Added materials: {', '.join(added)}")
        # Print failures
        if failed:
            print("⚠ Some materials could not be added:")
            for name, reason in failed:
                print(f"  - {name}: {reason}")

    def create_circuits(self):
        """Create 3 coil circuits CoilA, CoilB and CoilC."""
        for coil_label in ["A", "B", "C"]:
            circuit_name = f"Coil{coil_label}"
            # Create coil circuit property (starting current 0, series connection)
            femm.mi_addcircprop(circuit_name, 0, 1)

    def create_magnets(self):
        """Create magnets of the tubular linear motor from specified parameters."""

        # Initial offset to center the full magnet stack around Y = 0
        total_height = (self.magnet.number - 1) * self.magnet.pitch
        y_start = -total_height / 2

        for i in range(self.magnet.number):
            # Compute the vertical center position of the current magnet
            y_center = y_start + i * self.magnet.pitch
            half_length = self.magnet.length / 2
            r = self.magnet.od / 2

            # Define the rectangle corners in clockwise order
            top_left = (0, y_center + half_length)
            bottom_left = (0, y_center - half_length)
            bottom_right = (r, y_center - half_length)
            top_right = (r, y_center + half_length)

            # Add 4 nodes at the corners
            femm.mi_addnode(*top_left)
            femm.mi_addnode(*bottom_left)
            femm.mi_addnode(*bottom_right)
            femm.mi_addnode(*top_right)

            # Connect the nodes with 4 segments (lines)
            femm.mi_addsegment(*top_left, *bottom_left)
            femm.mi_addsegment(*bottom_left, *bottom_right)
            femm.mi_addsegment(*bottom_right, *top_right)
            femm.mi_addsegment(*top_right, *top_left)

            # Compute the center of the rectangle (for placing the block label)
            x_center = r / 2

            # Determine magnetization direction: alternate 0° and 180°
            magnetization_angle = -90 if i % 2 == 0 else 90

            # Add block label and assign magnetization
            femm.mi_addblocklabel(x_center, y_center)
            femm.mi_selectlabel(x_center, y_center)
            femm.mi_setblockprop(
                self.magnet.material,  # Magnet material (e.g., "NdFeB 42")
                1,  # Automesh
                0,  # Mesh size
                "",  # Circuit
                magnetization_angle,  # Direction of magnetization (deg)
                0,  # Group
                0,  # Turns
            )
            femm.mi_clearselected()

    def create_coils(self):
        """Create coils of the tubular linear motor from specified parameters."""

        # coil_labels = ['A', 'B', 'C']
        coil_labels = [("A", 1), ("B", 2), ("C", 3)]

        # Initial offset to center the full magnet stack around Y = 0
        total_height = (self.coil.number - 1) * self.coil.pitch
        y_start = -total_height / 2

        for i in range(self.coil.number):
            # Determine the current coil label (A, B, or C)
            # coil_label = coil_labels[(self.coil.number - 1 - i) % 3]
            coil_label, group = coil_labels[(self.coil.number - 1 - i) % 3]

            # Compute the vertical center position of the current magnet
            y_center = y_start + i * self.coil.pitch
            half_length = self.coil.length / 2
            r = self.coil.od / 2
            x_start = self.coil.id / 2

            # Define the rectangle corners in clockwise order
            top_left = (x_start, y_center + half_length)
            bottom_left = (x_start, y_center - half_length)
            bottom_right = (r, y_center - half_length)
            top_right = (r, y_center + half_length)

            # Add 4 nodes at the corners
            femm.mi_addnode(*top_left)
            femm.mi_addnode(*bottom_left)
            femm.mi_addnode(*bottom_right)
            femm.mi_addnode(*top_right)

            # Connect nodes with 4 segments (lines)
            segments = [
                (top_left, bottom_left),
                (bottom_left, bottom_right),
                (bottom_right, top_right),
                (top_right, top_left),
            ]
            for p1, p2 in segments:
                femm.mi_addsegment(*p1, *p2)
                # Sélectionner le segment par son centre pour l'affecter à un groupe
                x_seg = (p1[0] + p2[0]) / 2
                y_seg = (p1[1] + p2[1]) / 2
                femm.mi_selectsegment(x_seg, y_seg)
                femm.mi_setsegmentprop("<None>", 0, 1, 0, group)
                femm.mi_clearselected()

            # Compute the center of the rectangle (for placing the block label)
            x_center = x_start + (r - x_start) / 2

            # Determine group index (0, 1, 2, ...) → group of 3 coils
            group_index = i // 3
            # True if group is even (0, 2, ...) → pattern: + - +
            # False if group is odd (1, 3, ...) → pattern: - + -
            if group_index % 2 == 0:
                nb_turns = (
                    self.coil.nb_turn if coil_label == "B" else -self.coil.nb_turn
                )
            else:
                nb_turns = (
                    -self.coil.nb_turn if coil_label == "B" else self.coil.nb_turn
                )

            femm.mi_addblocklabel(x_center, y_center)
            femm.mi_selectlabel(x_center, y_center)
            femm.mi_setblockprop(
                self.coil.material,  # Material name
                1,  # Automesh
                0,  # Mesh size
                f"Coil{coil_label}",  # Circuit name
                0,  # Magnetization angle (not used here)
                group,  # Group number
                nb_turns,  # Number of turns
            )
            femm.mi_clearselected()

    def create_auto_boundary(self):
        """Automatically create an open boundary region around the model."""
        # Get maximum radius among magnets and coils
        r_max = max(self.coil.od / 2, self.magnet.od / 2)
        # Compute total height of the magnet stack (symmetrically centered on Y=0)
        h_stack = (self.magnet.number - 1) * self.magnet.pitch + self.magnet.length
        # Estimate total half-height including coils for margin
        h_max = h_stack / 2 + self.coil.length
        # Compute the radial distance needed to enclose the entire model
        model_radius = (r_max**2 + h_max**2) ** 0.5
        # Add a safety margin
        air_radius = model_radius * 1.5

        # Generate the open boundary using FEMM's automatic boundary constructor
        femm.mi_makeABC(
            7,  # Nb shells [1 - 10]
            air_radius,  # Radius of the open boundary
            0,  # x center
            0,  # y center
            0,  # Dirichlet
        )

        # Add Air block
        air_x = air_radius / 2  # Halfway in radius direction
        air_y = air_radius * 2 / 3  # 2/3 in vertical axis
        femm.mi_addblocklabel(air_x, air_y)
        femm.mi_selectlabel(air_x, air_y)
        femm.mi_setblockprop(
            "Air",  # Material name
            1,  # Automesh
            0,  # Mesh size (0 = default)
            "",  # No circuit
            0,  # Magnetization angle (not used here)
            0,  # Group number
            0,  # Number of turns
        )
        femm.mi_clearselected()


class FEMMModel:
    """Handles loading, translating, and solving a FEMM model."""

    def __init__(
        self, model_path: Path, amplitude: float, period: float, coil_length: float
    ):
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
        angle = (
            2 * math.pi * pos / self.period
            + phase
            + 2 * math.pi * self.coil_length / self.period
        )
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
    plt.savefig("Results_Force_Currents.png")
    plt.show()


if __name__ == "__main__":

    # Select if you want to "generate" a FEMM model or "load" an existing
    MODE = "generate"
    # MODE = "load"

    # Simulation parameters
    START_POS = -20
    END_POS = 20
    STEP_SIZE = 1

    # Model parameters
    PEAK_CURRENT = 3
    PERIOD = 40.0  # length of 2 magnets
    COIL_LENGTH = 6.8

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
            amplitude=PEAK_CURRENT,
            period=PERIOD,
            coil_length=COIL_LENGTH,
        )
    except Exception as e:
        print(f"Simulation error: {e}")
        sys.exit(1)

    simulation_data = run_simulation(fem_model, START_POS, END_POS, STEP_SIZE)
    df = pd.json_normalize(simulation_data).set_index("Position")
    df.to_csv("SimulationResults.csv")
    plot_results(df)
    print("Simulation completed successfully. Results saved in SimulationResults.csv")
