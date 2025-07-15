from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict
import math
import femm


@dataclass
class FEMMModel:
    """Handles loading, translating, and solving a FEMM model."""
    peak_current: float
    pole_length: float
    coil_pitch: float
    model_path: Path
    output_path: Path = field(default_factory=lambda: Path("out/SimOutput.fem"))
    offset_pos: float = 0.0
    currents: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        femm.openfemm(1)
        femm.opendocument(str(self.model_path))
        femm.mi_probdef(0, "millimeters", "axi")

    def mesh_and_solve(self):
        """Save, mesh, and run the simulation."""
        femm.mi_saveas(self.output_path.resolve().as_posix())
        femm.mi_createmesh()
        femm.mi_analyze()

    def compute_current_at_position(self, pos: float, phase: float = 0.0) -> float:
        """Compute coil currents from position and model parameters"""
        angle = (
            2 * math.pi * pos / self.pole_length
            + phase
            + 2 * math.pi * self.coil_pitch / self.pole_length
        )
        return self.peak_current * math.sin(angle)

    def translate_and_set_currents(self, delta: float):
        """Translate the model and update coil currents."""
        femm.mi_clearselected()
        femm.mi_seteditmode("group")
        for group_id in range(1, 5):
            femm.mi_selectgroup(group_id)
        femm.mi_movetranslate(0, delta)
        self.offset_pos += delta
        self.currents = {
            "CoilA": self.compute_current_at_position(self.offset_pos, 0),
            "CoilB": self.compute_current_at_position(self.offset_pos, 2 * math.pi / 3),
            "CoilC": self.compute_current_at_position(self.offset_pos, -2 * math.pi / 3),
        }
        for coil, current in self.currents.items():
            femm.mi_setcurrent(coil, current)
