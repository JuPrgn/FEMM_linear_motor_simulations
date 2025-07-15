from dataclasses import dataclass, field
from typing import Dict
import femm


@dataclass
class SimulationResult:
    """Stores and extracts forces and currents from a solved FEMM model."""
    position: float
    currents: Dict[str, float]
    results: Dict = field(default_factory=dict)

    def __init__(self, femm_model):
        self.position = femm_model.offset_pos
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
        femm.mo_clearblock()
        for group in [1, 2, 3]:
            femm.mo_groupselectblock(group)
        total_force = femm.mo_blockintegral(19)
        self.results["Force"]["Sum"] = total_force
        femm.mo_clearblock()
