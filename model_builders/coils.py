"""
Functions to build coils geometry in FEMM.
"""


def create_coil_geometry(femm, x_start, r, y_center, half_length, group):
    """Draw a single coil rectangle in FEMM."""
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
    return x_start + (r - x_start) / 2

def add_coil_block(femm, x_center, y_center, coil, coil_label, group, nb_turns):
    """Add block label and set coil properties."""
    femm.mi_addblocklabel(x_center, y_center)
    femm.mi_selectlabel(x_center, y_center)
    femm.mi_setblockprop(
        coil.material,
        1,
        0,
        f"Coil{coil_label}",
        0,
        group,
        nb_turns,
    )
    femm.mi_clearselected()

def create_spool(femm, coil, y_center, half_length, r):
    """Draw spool around coil if needed."""
    coil_bottom_right = (r, y_center - half_length)
    coil_top_right = (r, y_center + half_length)
    spool_flange_length = coil.spool_flange_width
    half_spool_length = half_length + spool_flange_length
    spool_center_y = y_center
    spool_start_x = coil.spool_id / 2
    spool_end_x = coil.spool_od / 2
    spool_top_left = (spool_start_x, spool_center_y + half_spool_length)
    spool_bottom_left = (spool_start_x, spool_center_y - half_spool_length)
    spool_bottom_right = (spool_end_x, spool_center_y - half_spool_length)
    spool_bottom_right_upper_flange = (spool_end_x, spool_center_y - half_spool_length + spool_flange_length)
    spool_top_right = (spool_end_x, spool_center_y + half_spool_length)
    spool_top_right_inner_flange = (spool_end_x, spool_center_y + half_spool_length - spool_flange_length)
    femm.mi_addnode(*spool_top_left)
    femm.mi_addnode(*spool_bottom_left)
    femm.mi_addnode(*spool_bottom_right)
    femm.mi_addnode(*spool_bottom_right_upper_flange)
    femm.mi_addnode(*spool_top_right)
    femm.mi_addnode(*spool_top_right_inner_flange)
    spool_segments = [
        (spool_top_left, spool_bottom_left),
        (spool_bottom_left, spool_bottom_right),
        (spool_bottom_right, spool_bottom_right_upper_flange),
        (spool_bottom_right_upper_flange, coil_bottom_right),
        (coil_top_right, spool_top_right_inner_flange),
        (spool_top_right_inner_flange, spool_top_right),
        (spool_top_right, spool_top_left),
    ]
    for p1, p2 in spool_segments:
        femm.mi_addsegment(*p1, *p2)
        x_seg = (p1[0] + p2[0]) / 2
        y_seg = (p1[1] + p2[1]) / 2
        femm.mi_selectsegment(x_seg, y_seg)
        femm.mi_setsegmentprop("<None>", 0, 1, 0, 4)
        femm.mi_clearselected()
    spool_label_x = spool_start_x + (spool_end_x - spool_start_x) / 2
    spool_label_y = spool_center_y + half_spool_length - spool_flange_length / 2
    femm.mi_addblocklabel(spool_label_x, spool_label_y)
    femm.mi_selectlabel(spool_label_x, spool_label_y)
    femm.mi_setblockprop(
        coil.spool_material,
        1,
        0,
        "",
        0,
        4,
        0,
    )
    femm.mi_clearselected()

def create_coil_spacer(femm, coil, y_center, x_start, r):
    """Draw spacer between coils if needed."""
    spacer_length = coil.pitch - (coil.length + 2 * coil.spool_flange_width)
    spacer_center_y = y_center + coil.pitch / 2
    half_spacer = spacer_length / 2
    if coil.spool_id != 0:
        spacer_start_x = min(x_start, coil.spool_id / 2)
    else:
        spacer_start_x = x_start
    spacer_end_x = max(r, coil.spool_od / 2)
    spacer_top_left = (spacer_start_x, spacer_center_y + half_spacer)
    spacer_bottom_left = (spacer_start_x, spacer_center_y - half_spacer)
    spacer_bottom_right = (spacer_end_x, spacer_center_y - half_spacer)
    spacer_top_right = (spacer_end_x, spacer_center_y + half_spacer)
    femm.mi_addnode(*spacer_top_left)
    femm.mi_addnode(*spacer_bottom_left)
    femm.mi_addnode(*spacer_bottom_right)
    femm.mi_addnode(*spacer_top_right)
    spacer_segments = [
        (spacer_top_left, spacer_bottom_left),
        (spacer_bottom_left, spacer_bottom_right),
        (spacer_bottom_right, spacer_top_right),
        (spacer_top_right, spacer_top_left),
    ]
    for p1, p2 in spacer_segments:
        femm.mi_addsegment(*p1, *p2)
        x_seg = (p1[0] + p2[0]) / 2
        y_seg = (p1[1] + p2[1]) / 2
        femm.mi_selectsegment(x_seg, y_seg)
        femm.mi_setsegmentprop("<None>", 0, 1, 0, 4)
        femm.mi_clearselected()
    spacer_label_x = spacer_start_x + (spacer_end_x - spacer_start_x) / 2
    spacer_label_y = spacer_center_y
    femm.mi_addblocklabel(spacer_label_x, spacer_label_y)
    femm.mi_selectlabel(spacer_label_x, spacer_label_y)
    femm.mi_setblockprop(
        coil.spacer_material,
        1,
        0,
        "",
        0,
        4,
        0,
    )
    femm.mi_clearselected()

def create_coils(femm, coil):
    """
    Create coils of the tubular linear motor from specified parameters.
    This function draws each coil, adds spools and spacers if needed.
    """
    coil_labels = [("A", 1), ("B", 2), ("C", 3)]
    total_height = (coil.number - 1) * coil.pitch
    y_start = -total_height / 2 + coil.vertical_offset
    for i in range(coil.number):
        coil_label, group = coil_labels[(coil.number - 1 - i) % 3]
        y_center = y_start + i * coil.pitch
        half_length = coil.length / 2
        r = coil.od / 2
        x_start = coil.id / 2
        # Draw coil geometry
        x_center = create_coil_geometry(femm, x_start, r, y_center, half_length, group)
        group_index = i // 3
        if group_index % 2 == 0:
            nb_turns = coil.nb_turn if coil_label == "B" else -coil.nb_turn
        else:
            nb_turns = -coil.nb_turn if coil_label == "B" else coil.nb_turn
        add_coil_block(femm, x_center, y_center, coil, coil_label, group, nb_turns)

        # Add spool if needed
        if (
            coil.spool_flange_width > 0
            and coil.spool_id <= coil.id
            and coil.spool_od >= coil.od
        ):
            create_spool(femm, coil, y_center, half_length, r)

        # Add spacer if needed
        if (coil.length + 2 * coil.spool_flange_width) < coil.pitch and i < coil.number - 1:
            create_coil_spacer(femm, coil, y_center, x_start, r)
