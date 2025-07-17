"""
Data class for magnet parameters used in FEMM simulations.
"""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Magnet:
    """Magnet parameters for FEMM simulation."""
    od: Optional[float] = None
    length: Optional[float] = None
    pitch: Optional[float] = None
    material: Optional[str] = None
    spacer_material: Optional[str] = None
    number: Optional[int] = None
    tube_od: Optional[float] = None
    tube_material: Optional[str] = None

    def __repr__(self):
        return f"<Magnet OD={self.od}, Length={self.length}, Pitch={self.pitch}>"
