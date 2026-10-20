"""Gridfinity baseplate socket profile constants (mm)."""

PITCH = 42.0
CLEARANCE = 0.0          # baseplate top opening is full pitch (42.0 mm); clearance is on the bin
TOP_CHAMFER = 0.7        # 45 deg
VERTICAL = 1.8
BOTTOM_CHAMFER = 2.15    # 45 deg
PROFILE_HEIGHT = TOP_CHAMFER + VERTICAL + BOTTOM_CHAMFER  # 4.65
MAGNET_FRAME_HEIGHT = 4.4  # height of the lower magnet frame section
CORNER_RADIUS = 4.0      # at the socket opening (42 mm nominal)
MAGNET_DIAMETER = 6.5
MAGNET_DEPTH = 2.4
SCREW_DIAMETER = 3.0     # through-hole in magnet tab center
MAGNET_OFFSET = 8.0      # hole center from nominal cell edge (4.8mm inside 35.6mm bottom opening)
TAB_INNER_OFFSET = 13.0  # inner edge of corner tab from nominal cell edge (8.0 + 3.25 + 1.75 wall)
TAB_FILLET_RADIUS = 5.0  # concentric with the magnet hole at 8.0 mm (13.0 - 5.0 = 8.0)

# Laser-cut 2D baseplate defaults:
# A Gridfinity bin foot bottom is 35.6 mm x 35.6 mm (3.2 mm inset per side from 42 mm pitch),
# leaving a 6.4 mm rib between adjacent cutouts (or ~5.7 mm at mid-chamfer).
LASER_WALL_WIDTH = 5.7   # rib width between adjacent cell cutouts (mm) -> 36.3 mm cutout
LASER_CORNER_RADIUS = 1.6  # corner radius at bottom of Gridfinity bin foot (mm)

# (depth below plate top, inset from opening, extrude_depth, taper_deg) for each cut layer.
LAYERS = [
    (0.0, 0.0, TOP_CHAMFER, 45.0),
    (TOP_CHAMFER, TOP_CHAMFER, VERTICAL, 0.0),
    (TOP_CHAMFER + VERTICAL, TOP_CHAMFER, BOTTOM_CHAMFER, 45.0),
]
