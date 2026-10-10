"""Per-part real-solid sanity evidence; P2 clearance checks remain separate."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cad.config import load_parameters
from cad.model import build_assembly
_,p=load_parameters();a=build_assembly(p)
report={"stage":"P1","parts":{},"interfaces":a.interfaces,"limits":"Solid validity only; P2 pending."}
for key,s in a.parts.items():
    b=s.bounding_box()
    report["parts"][key]={"valid":s.is_valid,"solid_count":len(s.solids()),"volume_mm3":s.volume,
                         "bbox_mm":{"min":[b.min.X,b.min.Y,b.min.Z],"max":[b.max.X,b.max.Y,b.max.Z]}}
out=ROOT/"artifacts"/"p1";out.mkdir(parents=True,exist_ok=True)
(out/"p1-solids.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2))
assert all(x["valid"] and x["solid_count"]==1 and x["volume_mm3"]>0 for x in report["parts"].values())
