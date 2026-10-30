"""Fixed simulation settings for Stormwatch Harbour (same for every student)."""

GRID_W = 24            # columns, x = 0..23 (west -> east)
GRID_H = 16            # rows,    y = 0..15 (north -> south)

# Four berths along the north edge (row 0).
BERTHS = {
    "B1": (3, 0),
    "B2": (9, 0),
    "B3": (15, 0),
    "B4": (21, 0),
}
UNSAFE_BERTHS = ("B1", "B4")     # unsafe during a storm
SAFE_BERTHS = ("B2", "B3")

# Warehouse in the south-west corner.
WAREHOUSE = (0, 15)

# An agent is in a berth's danger zone if it is within this many columns
# of an unsafe berth and in rows 0..UNSAFE_DEPTH.
UNSAFE_RADIUS_X = 2
UNSAFE_DEPTH = 2

N_WORKERS = 10
SHIP_INTERVAL = (6, 10)          # ticks between ship arrivals (inclusive)
CARGO_PER_SHIP = 8
RUN_TICKS = 600

N_STORMS = 3
STORM_LENGTH = 15
WARNING_LEAD = 5                 # Lookout warns 5 ticks before a storm

KNOCKOUT_TICKS = 20              # a knocked-out worker is out of action this long

MAIN_SEEDS = [11, 12, 13]        # seeds required by Tasks 2 and 3
EXTRA_SEEDS = [11, 12, 13, 14, 15]  # full evaluation range from settings table

HM_CALL_EVERY = 10               # Harbour Master is consulted every 10 ticks
HOLD_TICKS = 20                  # hold_ship keeps a ship off unsafe berths this long
