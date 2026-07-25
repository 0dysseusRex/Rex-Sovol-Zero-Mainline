; Sovol Zero — Mainline Klipper start g-code
; For Orca Slicer / Creality Print (Sovol OEM fork)
;
; PRINT_START handles: homing, bed/chamber heat, load cell Z offset,
; eddy mesh, skew profile, and adaptive LINE_PURGE.
; Do NOT duplicate heat, home, purge, or extrude here.
;
; Enable "Exclude Objects" in the slicer for adaptive line purge placement.

M117
START_PRINT BED=[bed_temperature_initial_layer_single] HOTEND=[nozzle_temperature_initial_layer] CHAMBER=[chamber_temperature]
SET_PRINT_STATS_INFO TOTAL_LAYER=[total_layer_count]
G90
