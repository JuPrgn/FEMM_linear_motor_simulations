from pathlib import Path
import yaml
import femm

from magnet import Magnet
from coil import Coil


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
        self.magnet = Magnet(**{k.lower(): v for k, v in magnet_data.items()})
        self.coil = Coil(**{k.lower(): v for k, v in coil_data.items()})

    def validate_params(self):
        """Checks that the yaml file contains necessary keys."""
        # Check presence of main sections
        if "Coil" not in self.params:
            raise ValueError("Missing required section: 'Coil'")
        if "Magnet" not in self.params:
            raise ValueError("Missing required section: 'Magnet'")

        # List of required fields for Magnet and Coil
        required_magnet = ["number", "pitch", "length", "od", "material"]
        required_coil = ["number", "pitch", "length", "od", "id", "nb_turn", "material"]

        # Check Magnet fields
        for field in required_magnet:
            value = getattr(self.magnet, field, None)
            if value is None:
                raise ValueError(f"Missing or null parameter in Magnet: '{field}'")

        # Check Coil fields
        for field in required_coil:
            value = getattr(self.coil, field, None)
            if value is None:
                raise ValueError(f"Missing or null parameter in Coil: '{field}'")

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
        found_materials = {}
        material_names.add("Air")
        for section_name, section_data in self.params.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if "material" in key.lower() and isinstance(value, str):
                        found_materials.setdefault(section_name, set()).add(value)
                        material_names.add(value)
        for section, materials in found_materials.items():
            print(f"Found materials in {section}: {', '.join(sorted(materials))}")
        added = []
        failed = []
        for material_name in sorted(material_names):
            try:
                femm.mi_getmaterial(material_name)
                added.append(material_name)
            except Exception as e:
                failed.append((material_name, str(e)))
        if added:
            print(f"✔ Added materials: {', '.join(added)}")
        if failed:
            print("⚠ Some materials could not be added:")
            for name, reason in failed:
                print(f"  - {name}: {reason}")

    def create_circuits(self):
        """Create 3 coil circuits CoilA, CoilB and CoilC."""
        for coil_label in ["A", "B", "C"]:
            circuit_name = f"Coil{coil_label}"
            femm.mi_addcircprop(circuit_name, 0, 1)

    def create_magnets(self):
        """Create magnets of the tubular linear motor from specified parameters."""
        total_height = (self.magnet.number - 1) * self.magnet.pitch
        y_start = -total_height / 2
        for i in range(self.magnet.number):
            y_center = y_start + i * self.magnet.pitch
            half_length = self.magnet.length / 2
            r = self.magnet.od / 2
            top_left = (0, y_center + half_length)
            bottom_left = (0, y_center - half_length)
            bottom_right = (r, y_center - half_length)
            top_right = (r, y_center + half_length)
            femm.mi_addnode(*top_left)
            femm.mi_addnode(*bottom_left)
            femm.mi_addnode(*bottom_right)
            femm.mi_addnode(*top_right)
            femm.mi_addsegment(*top_left, *bottom_left)
            femm.mi_addsegment(*bottom_left, *bottom_right)
            femm.mi_addsegment(*bottom_right, *top_right)
            femm.mi_addsegment(*top_right, *top_left)
            x_center = r / 2
            magnetization_angle = -90 if i % 2 == 0 else 90
            femm.mi_addblocklabel(x_center, y_center)
            femm.mi_selectlabel(x_center, y_center)
            femm.mi_setblockprop(
                self.magnet.material,
                1,
                0,
                "",
                magnetization_angle,
                0,
                0,
            )
            femm.mi_clearselected()

    def create_coils(self):
        """Create coils of the tubular linear motor from specified parameters."""
        coil_labels = [("A", 1), ("B", 2), ("C", 3)]
        total_height = (self.coil.number - 1) * self.coil.pitch
        y_start = -total_height / 2
        for i in range(self.coil.number):
            coil_label, group = coil_labels[(self.coil.number - 1 - i) % 3]
            y_center = y_start + i * self.coil.pitch
            half_length = self.coil.length / 2
            r = self.coil.od / 2
            x_start = self.coil.id / 2
            top_left = (x_start, y_center + half_length)
            bottom_left = (x_start, y_center - half_length)
            bottom_right = (r, y_center - half_length)
            top_right = (r, y_center + half_length)
            femm.mi_addnode(*top_left)
            femm.mi_addnode(*bottom_left)
            femm.mi_addnode(*bottom_right)
            femm.mi_addnode(*top_right)
            segments = [
                (top_left, bottom_left),
                (bottom_left, bottom_right),
                (bottom_right, top_right),
                (top_right, top_left),
            ]
            for p1, p2 in segments:
                femm.mi_addsegment(*p1, *p2)
                x_seg = (p1[0] + p2[0]) / 2
                y_seg = (p1[1] + p2[1]) / 2
                femm.mi_selectsegment(x_seg, y_seg)
                femm.mi_setsegmentprop("<None>", 0, 1, 0, group)
                femm.mi_clearselected()
            x_center = x_start + (r - x_start) / 2
            group_index = i // 3
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
                self.coil.material,
                1,
                0,
                f"Coil{coil_label}",
                0,
                group,
                nb_turns,
            )
            femm.mi_clearselected()

    def create_auto_boundary(self):
        """Automatically create an open boundary region around the model."""
        r_max = max(self.coil.od / 2, self.magnet.od / 2)
        h_stack = (self.magnet.number - 1) * self.magnet.pitch + self.magnet.length
        h_max = h_stack / 2 + self.coil.length
        model_radius = (r_max**2 + h_max**2) ** 0.5
        air_radius = model_radius * 1.5
        femm.mi_makeABC(
            7,
            air_radius,
            0,
            0,
            0,
        )
        air_x = air_radius / 2
        air_y = air_radius * 2 / 3
        femm.mi_addblocklabel(air_x, air_y)
        femm.mi_selectlabel(air_x, air_y)
        femm.mi_setblockprop(
            "Air",
            1,
            0,
            "",
            0,
            0,
            0,
        )
        femm.mi_clearselected()
