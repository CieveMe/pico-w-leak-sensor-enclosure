"""Load attributed inputs; reject nonphysical parameter sets."""
import json
import math
from pathlib import Path
DEFAULT = Path(__file__).with_name("parameters.json")

def load_parameters(path=DEFAULT, overrides=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for name, value in (overrides or {}).items():
        if name not in data["design_assumptions"]:
            raise ValueError(f"Unknown editable parameter: {name}")
        data["design_assumptions"][name]["value"] = value
    values = {k: v["value"] for group in ("manufacturer_dimensions", "design_assumptions")
              for k, v in data[group].items()}
    for key,value in values.items():
        if not isinstance(value,(float,int)) or not math.isfinite(value):
            raise ValueError(f"Nonfinite parameter: {key}")
        signed=("antenna_window_end_y","bracket_top_z","sensor_front_y","sensor_tilt_degrees")
        if key not in signed and value<=0:
            raise ValueError(f"{key} must be positive")
    if not 1<=values["wall_thickness"]<=5:
        raise ValueError("wall_thickness must be between 1 and 5 mm")
    if values["minimum_air_clearance"]<.1:
        raise ValueError("minimum_air_clearance must be at least 0.1 mm")
    if values["floor_thickness"]+values["pcb_support_height"]+1+values["pcb_component_height"]+values["minimum_air_clearance"]>=values["shell_height"]:
        raise ValueError("PCB/component stack leaves insufficient lid air clearance")
    if not 0<=values["sensor_tilt_degrees"]<=20:
        raise ValueError("sensor_tilt_degrees outside 0..20")
    if values["bracket_top_z"]>=0:
        raise ValueError("backplate base must be below shell")
    return data,values

def tolerance(data,name):
    return data["validation_tolerances"][name]["value"]
