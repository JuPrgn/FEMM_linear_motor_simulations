from dataclasses import dataclass
from typing import Optional


@dataclass
class Coil:
    """Coils parameters"""
    id: Optional[float] = None
    od: Optional[float] = None
    length: Optional[float] = None
    pitch: Optional[float] = None
    material: Optional[str] = None
    spacer_material: Optional[str] = None
    nb_turn: Optional[int] = None
    number: Optional[int] = None
    current_peak: Optional[float] = None
    vertical_offset: Optional[float] = None
    spool_id: Optional[float] = None
    spool_od: Optional[float] = None
    spool_flange_width: Optional[float] = None
    spool_material: Optional[str] = None
    tube_id: Optional[float] = None
    tube_od: Optional[float] = None
    tube_material: Optional[str] = None

    def __repr__(self):
        return f"<Coil ID={self.id}, OD={self.od}, material={self.material}>"
