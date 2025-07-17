"""
Functions to build magnets geometry in FEMM.
"""


def create_magnet_geometry(femm, r, y_center, half_length):
    """Draw a single magnet rectangle in FEMM."""
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
    return (r / 2, y_center)

def add_magnet_block(femm, x_center, y_center, material, angle):
    """Add block label and set magnet properties."""
    femm.mi_addblocklabel(x_center, y_center)
    femm.mi_selectlabel(x_center, y_center)
    femm.mi_setblockprop(
        material,
        1,
        0,
        "",
        angle,
        0,
        0,
    )
    femm.mi_clearselected()

def create_spacer(femm, r, spacer_center_y, half_spacer, spacer_material):
    """Draw a spacer between magnets."""
    spacer_top_left = (0, spacer_center_y + half_spacer)
    spacer_bottom_left = (0, spacer_center_y - half_spacer)
    spacer_bottom_right = (r, spacer_center_y - half_spacer)
    spacer_top_right = (r, spacer_center_y + half_spacer)
    femm.mi_addnode(*spacer_top_left)
    femm.mi_addnode(*spacer_bottom_left)
    femm.mi_addnode(*spacer_bottom_right)
    femm.mi_addnode(*spacer_top_right)
    femm.mi_addsegment(*spacer_top_left, *spacer_bottom_left)
    femm.mi_addsegment(*spacer_bottom_left, *spacer_bottom_right)
    femm.mi_addsegment(*spacer_bottom_right, *spacer_top_right)
    femm.mi_addsegment(*spacer_top_right, *spacer_top_left)
    spacer_label_x = r / 2
    spacer_label_y = spacer_center_y
    femm.mi_addblocklabel(spacer_label_x, spacer_label_y)
    femm.mi_selectlabel(spacer_label_x, spacer_label_y)
    femm.mi_setblockprop(
        spacer_material,
        1,
        0,
        "",
        0,
        0,
        0,
    )
    femm.mi_clearselected()

def create_tube(femm, r, magnet, tube_material):
    """Draw tube around magnets if needed."""
    tube_half_height = magnet.number * magnet.pitch / 2
    tube_r = magnet.tube_od / 2
    tube_top_left = (r, tube_half_height)
    tube_bottom_left = (r, -tube_half_height)
    tube_bottom_right = (tube_r, -tube_half_height)
    tube_top_right = (tube_r, tube_half_height)
    femm.mi_addnode(*tube_top_left)
    femm.mi_addnode(*tube_bottom_left)
    femm.mi_addnode(*tube_bottom_right)
    femm.mi_addnode(*tube_top_right)
    femm.mi_addsegment(*tube_top_left, *tube_bottom_left)
    femm.mi_addsegment(*tube_bottom_left, *tube_bottom_right)
    femm.mi_addsegment(*tube_bottom_right, *tube_top_right)
    femm.mi_addsegment(*tube_top_right, *tube_top_left)
    tube_label_x = tube_r - (tube_r - r) / 2
    tube_label_y = 0
    femm.mi_addblocklabel(tube_label_x, tube_label_y)
    femm.mi_selectlabel(tube_label_x, tube_label_y)
    femm.mi_setblockprop(
        tube_material,
        1,
        0,
        "",
        0,
        0,
        0,
    )
    femm.mi_clearselected()

def create_magnets(femm, magnet):
    """
    Create magnets of the tubular linear motor from specified parameters.
    This function draws each magnet, adds spacers if needed, and draws the tube if specified.
    """
    total_height = (magnet.number - 1) * magnet.pitch
    y_start = -total_height / 2
    r = magnet.od / 2
    for i in range(magnet.number):
        y_center = y_start + i * magnet.pitch
        half_length = magnet.length / 2
        # Draw magnet geometry
        x_center, y_center_label = create_magnet_geometry(femm, r, y_center, half_length)
        # Alternate magnetization angle for each magnet
        magnetization_angle = -90 if i % 2 == 0 else 90
        add_magnet_block(femm, x_center, y_center_label, magnet.material, magnetization_angle)

        # Add spacer if needed
        if magnet.length < magnet.pitch and i < magnet.number - 1:
            spacer_length = magnet.pitch - magnet.length
            spacer_center_y = y_center + magnet.pitch / 2
            half_spacer = spacer_length / 2
            create_spacer(femm, r, spacer_center_y, half_spacer, magnet.spacer_material)

    # Draw tube if needed
    if magnet.tube_od > magnet.od:
        create_tube(femm, r, magnet, magnet.tube_material)
