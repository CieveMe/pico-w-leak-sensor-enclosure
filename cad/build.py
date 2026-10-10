"""Build and validate a revision-consistent mechanical artifact set."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from cad.config import load_parameters,tolerance
from cad.model import build_assembly
from cad.runtime import bd
from cad.export import bbox,export_glb,digest
from cad.validate import geometry_checks,Checks

NAMES={"lower_shell":"主机下壳","lid":"螺钉上盖","wall_bracket":"壁挂背板",
       "probe_holder":"探头托架","pico_w":"Pico W 简化包络","water_sensor":"SEN0121 简化包络"}
COLORS={"lower_shell":"#627876","lid":"#d5dbd1","wall_bracket":"#454c53","probe_holder":"#dc8c4c",
        "pico_w":"#277a56","water_sensor":"#bd963d"}
EXPLODE={"lower_shell":[0,0,0],"lid":[0,0,35],"wall_bracket":[0,0,-20],
         "probe_holder":[20,0,0],"pico_w":[0,0,12],"water_sensor":[20,0,18]}
LIMITS=[
 "Simplified nominal component, socket, plug, cable, solder and sensing-region envelopes.",
 "No physical fit/print, RF, fastening strength, alarm, waterproofing or certification test.",
 "STEP OCP reimport is digital serialization checking; independent CAD application not yet verified.",
 "GLB/STL are meshes; STEP and Python are the engineering source.",
 "Thread bite is intentionally unmodeled; pilot and fastener dimensions require hardware calibration.",
 "Sensor sensing depth and connector exposure require real trials."
]

def source_revision(data):
    h=hashlib.sha256()
    for path in sorted((ROOT/"cad").glob("*.py")):
        h.update(path.name.encode()+b"\0"+path.read_bytes()+b"\0")
    h.update(json.dumps(data,sort_keys=True,separators=(",",":")).encode())
    return "sha256:"+h.hexdigest()

def stl_bbox(path):
    raw=path.read_bytes();n=struct.unpack_from("<I",raw,80)[0]
    if len(raw)!=84+50*n or n==0: raise ValueError("Not a nonempty binary STL")
    points=[struct.unpack_from("<3f",raw,84+i*50+12+j*12) for i in range(n) for j in range(3)]
    return {"min":[min(p[k] for p in points) for k in range(3)],
            "max":[max(p[k] for p in points) for k in range(3)]}

def bbox_error(a,b):
    return max(abs(a[key][i]-b[key][i]) for key in ("min","max") for i in range(3))

def generate(output,overrides=None,variant="baseline",pcb_shift=(0,0,0)):
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    # A failed regeneration must not leave a healthy manifest from an earlier run.
    manifest_path=out/"manifest.json"
    if manifest_path.exists(): manifest_path.unlink()
    data,p=load_parameters(overrides=overrides)
    revision=source_revision(data);a=build_assembly(p,pcb_shift)
    checks=geometry_checks(a,data)
    entries=[]
    for key,shape in {**a.parts,**a.references}.items():
        files={};source=bbox(shape)
        role="custom" if key in a.parts else "reference"
        if role=="custom":
            step=out/(key+".step")
            if not bd.export_step(shape,step,unit=bd.Unit.MM): raise RuntimeError("STEP export returned false")
            reopened=bd.import_step(step)
            checks.eq("step.valid",[key],reopened.is_valid,True,"boolean")
            checks.eq("step.solid_count",[key],len(reopened.solids()),1,"count")
            checks.le("step.bbox_max_error",[key],bbox_error(source,bbox(reopened)),tolerance(data,"step_bbox"),"mm")
            checks.le("step.relative_volume_error",[key],abs(shape.volume-reopened.volume)/shape.volume,
                      tolerance(data,"step_relative_volume"),"ratio")
            files["step"]=step.name
            stl=out/(key+".stl")
            if not bd.export_stl(shape,stl,tolerance=.001,angular_tolerance=.1): raise RuntimeError("STL export returned false")
            checks.le("stl.bbox_max_error",[key],bbox_error(source,stl_bbox(stl)),.1,"mm",
                      "Binary STL vertices in assembled CAD mm; not an engineering solid.")
            files["stl"]=stl.name
        glb=out/(key+".glb")
        measured=export_glb(shape,glb,tolerance(data,"mesh_deflection"),tolerance(data,"mesh_angular_deflection"))
        checks.le("glb.world_bbox_max_error",[key],bbox_error(source,measured),tolerance(data,"glb_bbox"),"mm",
                  "Scene-node world vertices restored by scale 1000/Rx(+90), compared to CAD source.")
        files["glb"]=glb.name
        entries.append(dict(id=key,name=NAMES[key],role=role,files=files,color=COLORS[key],
                            explode=EXPLODE[key],bbox=source,volume_mm3=shape.volume,
                            file_sha256={fmt:digest(out/name) for fmt,name in files.items()}))
    total=bd.Compound(children=list(a.parts.values())+list(a.references.values()),label="assembled_prototype")
    assembly=out/"assembly.step"
    if not bd.export_step(total,assembly,unit=bd.Unit.MM): raise RuntimeError("Assembly STEP export false")
    reopened=bd.import_step(assembly)
    checks.eq("assembly.source_part_count",["assembly"],len(total.children),6,"count")
    checks.eq("assembly.reimport_solid_count",["assembly"],len(reopened.solids()),len(total.solids()),"count")
    checks.eq("assembly.reimport_component_count",["assembly"],len(reopened.children),6,"count",
              "Imported labeled top-level components; two are simplified references.")
    checks.le("assembly.bbox_max_error",["assembly"],bbox_error(bbox(total),bbox(reopened)),.01,"mm")
    checks.le("assembly.relative_volume_error",["assembly"],abs(sum(s.volume for s in total.solids())-sum(s.volume for s in reopened.solids()))/sum(s.volume for s in total.solids()),1e-5,"ratio")
    for source_child,imported_child in zip(total.children,reopened.children):
        checks.eq("assembly.component_label",[source_child.label],imported_child.label,source_child.label,"label")
        checks.le("assembly.component_bbox",[source_child.label],bbox_error(bbox(source_child),bbox(imported_child)),.01,"mm")
        v0=sum(s.volume for s in source_child.solids());v1=sum(s.volume for s in imported_child.solids())
        checks.le("assembly.component_volume",[source_child.label],abs(v0-v1)/v0,1e-5,"ratio")
    step_text=assembly.read_text(encoding="utf-8",errors="replace")
    checks.eq("assembly.step_mm_unit",["assembly"],"SI_UNIT(.MILLI.,.METRE.)" in step_text,True,"boolean")
    checks.rows.append(dict(name="independent_cad_app.reopen",objects=["assembly.step"],
        status="unverified",measured=None,threshold={"requires":"independent CAD app: 6 components, mm and key dimensions"},
        unit="review",detail="OCP reimport above is separate. No FreeCAD/SolidWorks application result claimed."))
    failures=[r for r in checks.rows if r["status"]=="failed"]
    report=dict(schema_version=1,variant=variant,source_revision=revision,units="mm",cad_up_axis="Z",
                digital_checks_pass=not failures,status="failed" if failures else "digital_passed_with_unverified_items",
                check_count=len(checks.rows),failed_count=len(failures),unverified_count=1,
                checks=checks.rows,limitations=LIMITS)
    (out/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    (out/"parameters.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    manifest=dict(schema_version=1,variant=variant,source_revision=revision,units="mm",cad_up_axis="Z",
                  glb_units="m",up_axis="Y",parts=entries,parameters="parameters.json",
                  validation="validation.json",assembly="assembly.step",interfaces=a.interfaces,
                  limitations=LIMITS,assembly_sha256=digest(assembly),validation_sha256=digest(out/"validation.json"))
    if not failures:
        manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    return report,a

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",default="artifacts/baseline")
    parser.add_argument("--variant",default="baseline")
    parser.add_argument("--set",action="append",default=[],metavar="PARAM=NUMBER")
    args=parser.parse_args();overrides={}
    out=Path(args.output)
    try:
        for item in args.set:
            key,value=item.split("=",1);overrides[key]=float(value)
        report,_=generate(out,overrides,args.variant)
    except Exception as error:
        out.mkdir(parents=True,exist_ok=True)
        (out/"manifest.json").unlink(missing_ok=True)
        failed=dict(status="failed",digital_checks_pass=False,error_type=type(error).__name__,
                    error=str(error).replace(str(ROOT),"<project>"))
        (out/"validation.json").write_text(json.dumps(failed,indent=2),encoding="utf-8")
        print(json.dumps(failed));return 1
    print(json.dumps({k:report[k] for k in ("variant","source_revision","digital_checks_pass","failed_count","unverified_count")}))
    for row in report["checks"]:
        if row["status"]=="failed": print(json.dumps(row,ensure_ascii=False))
    return 0 if report["digital_checks_pass"] else 1

if __name__=="__main__":raise SystemExit(main())
