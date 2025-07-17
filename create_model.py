from pathlib import Path
import yaml
import femm


from motor_dataclasses import Magnet, Coil
from model_builders.magnets import create_magnets
from model_builders.coils import create_coils
from model_builders.boundaries import create_auto_boundary


class CreateModel:
    """Handles creating a FEMM model, translating, and solving a FEMM model."""

    def __init__(self, model_path: Path):
        self.model_path = model_path
        self.params_dict = {}
        self.magnet_params = None
        self.coil_params = None
        self.exp_factor = 0.5
        self.moving_mass = 0
        self.output_path = Path.cwd() / "SimGenerated.fem"

    def build(self):
        """Build the model from YAML file specified parameters"""
        self.load_model_parameters()
        self.validate_params()
        femm.openfemm(1)
        analysis_types = {
            "Magnetic": 0,
            "Electrostatic": 1,
            "Heat Flow": 2,
            "Current Flow": 3,
        }
        femm.newdocument(analysis_types["Magnetic"])
        femm.mi_probdef(0, "millimeters", "axi")
        self.import_materials_property()
        self.create_circuits()
        self.create_magnets()
        self.create_coils()
        self.create_auto_boundary()
        femm.mi_saveas(str(self.output_path))

    def load_model_parameters(self):
        """Import model parameters from YAML file."""
        try:
            with open(self.model_path, "r", encoding="utf-8") as f:
                self.params_dict = yaml.safe_load(f)
                if not isinstance(self.params_dict, dict):
                    raise ValueError("YAML root must be a dictionary")
        except FileNotFoundError:
            raise FileNotFoundError(f"Model file not found: {self.model_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error while reading parameters: {e}")
        self._load_objects()

    def _load_objects(self):
        magnet_data = self.params_dict.get("Magnet", {})
        coil_data = self.params_dict.get("Coil", {})
        self.magnet_params = Magnet(**{k.lower(): v for k, v in magnet_data.items()})
        self.coil_params = Coil(**{k.lower(): v for k, v in coil_data.items()})

    def validate_params(self):
        """Checks that the yaml file contains necessary keys."""
        # Check presence of main sections
        if "Coil" not in self.params_dict:
            raise ValueError("Missing required section: 'Coil'")
        if "Magnet" not in self.params_dict:
            raise ValueError("Missing required section: 'Magnet'")

        # List of required fields for Magnet and Coil
        required_magnet = ["number", "pitch", "length", "od", "material"]
        required_coil = ["number", "pitch", "length", "od", "id", "nb_turn", "material"]

        # Check Magnet fields
        for field in required_magnet:
            value = getattr(self.magnet_params, field, None)
            if value is None:
                raise ValueError(f"Missing or null parameter in Magnet: '{field}'")

        # Check Coil fields
        for field in required_coil:
            value = getattr(self.coil_params, field, None)
            if value is None:
                raise ValueError(f"Missing or null parameter in Coil: '{field}'")

    def get_param(self, *keys, default=None):
        """Access a nested parameter using a sequence of keys."""
        current = self.params_dict
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
        for section_name, section_data in self.params_dict.items():
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
        """Create magnets using external builder."""
        create_magnets(femm, self.magnet_params)


    def create_coils(self):
        """Create coils using external builder."""
        create_coils(femm, self.coil_params)

    def create_auto_boundary(self):
        """Create boundary using external builder."""
        create_auto_boundary(femm, self.coil_params, self.magnet_params)
