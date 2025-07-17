"""
Functions to build boundary geometry in FEMM.
"""

def create_auto_boundary(femm, coil, magnet):
    """Automatically create an open boundary region around the model."""
    r_max = max(coil.od / 2, magnet.od / 2)
    h_stack = (magnet.number - 1) * magnet.pitch + magnet.length
    h_max = h_stack / 2 + coil.length
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
