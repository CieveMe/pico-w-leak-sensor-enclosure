"""P2 review: read final files with fresh STEP imports and an independent GLB loader."""
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cad.runtime import bd
from cad.config import load_parameters
from cad.model import build_assembly,box
from cad.build import source_revision
from cad.export import export_glb

def bounds(shape):
    b=shape.bounding_box()
    return {"min":[b.min.X,b.min.Y,b.min.Z],"max":[b.max.X,b.max.Y,b.max.Z]}

def bound_error(left,right):
    return max(abs(left[k][i]-right[k][i]) for k in ("min","max") for i in range(3))

def volume(shape):
    return sum(s.volume for s in shape.solids())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def overlap(left,right):
    result=left.intersect(right)
    return sum(s.volume for s in result) if result else 0.0

def three_read(paths):
    result=subprocess.run(["node","scripts/review_glb_three.mjs",*[str(p) for p in paths]],
        cwd=ROOT,capture_output=True,encoding="utf-8",check=True)
    return json.loads(result.stdout)["results"]

def review_set(relative):
    out=ROOT/relative
    manifest=json.loads((out/"manifest.json").read_text(encoding="utf-8"))
    data,p=load_parameters(out/"parameters.json")
    assembly=build_assembly(p)
    assert manifest["source_revision"]==source_revision(data)
    assert sha(out/"assembly.step")==manifest["assembly_sha256"]
    assert sha(out/"validation.json")==manifest["validation_sha256"]
    report=json.loads((out/"validation.json").read_text(encoding="utf-8"))
    assert not [r for r in report["checks"] if r["status"]=="failed"]
    assert len([r for r in report["checks"] if r["status"]=="unverified"])==1
    source={**assembly.parts,**assembly.references}
    step_shapes={}
    items=[]
    glbs=three_read([out/e["files"]["glb"] for e in manifest["parts"]])
    for entry,glb in zip(manifest["parts"],glbs):
        name=entry["id"]; shape=source[name]
        for fmt,filename in entry["files"].items():
            assert sha(out/filename)==entry["file_sha256"][fmt]
        node_error=bound_error(bounds(shape),glb["bbox_mm"])
        assert node_error<.06,(name,node_error)
        # A wrong rotation can share an AABB; additionally measure actual sampled
        # loaded vertices against CAD surfaces, independent of cad.gltf's parser.
        sample_error=max(bd.Vertex(*v).distance_to(shape) for v in glb["surface_samples_mm"])
        assert sample_error<.06,(name,sample_error)
        item={"id":name,"glb_three_bbox_error_mm":node_error,
              "glb_three_surface_sample_error_mm":sample_error,
              "glb_vertices":glb["vertex_count"],"surface_sample_count":len(glb["surface_samples_mm"])}
        if entry["role"]=="custom":
            reopened=bd.import_step(out/entry["files"]["step"])
            assert reopened.is_valid and len(reopened.solids())==1
            error=bound_error(bounds(shape),bounds(reopened))
            verror=abs(volume(reopened)-volume(shape))/volume(shape)
            assert error<.01 and verror<1e-5
            step_shapes[name]=reopened
            item.update(step_bbox_error_mm=error,step_relative_volume_error=verror,
                        step_solid_count=len(reopened.solids()),step_valid=reopened.is_valid)
        items.append(item)
    pairs=[]
    for (n1,s1),(n2,s2) in itertools.combinations(step_shapes.items(),2):
        v=overlap(s1,s2);assert v<1e-6,(n1,n2,v)
        pairs.append({"objects":[n1,n2],"intersection_mm3":v})
    reopened=bd.import_step(out/"assembly.step")
    labels=[s.label for s in reopened.children]
    assert set(labels)==set(source) and len(labels)==6
    assert len(reopened.solids())==9 and reopened.is_valid
    assert 'SI_UNIT(.MILLI.,.METRE.)' in (out/"assembly.step").read_text(encoding="utf-8")
    for child in reopened.children:
        expected=source[child.label]
        assert bound_error(bounds(child),bounds(expected))<.01
        assert abs(volume(child)-volume(expected))/volume(expected)<1e-5
    return {"variant":manifest["variant"],"source_revision":manifest["source_revision"],
        "checks":len(report["checks"]),"unverified":1,"parts":items,
        "imported_custom_pairs":pairs,"assembly_labels":labels,"assembly_solid_count":9,
        "manifest_sha256":sha(out/"manifest.json"),"file_hashes_verified":True}

def nested_export(out):
    first=bd.Pos(11,-17,4)*bd.Rot(17,31,23)*box(12,7,5,(0,0,0))
    second=bd.Pos(-7,3,-2)*bd.Rot(9,11,13)*box(3,2,1,(0,0,0))
    inner=bd.Compound(children=[first,second],label="inner")
    inner.location=bd.Location((4,6,8),(7,19,29))
    outer=bd.Compound(children=[inner],label="outer")
    outer.location=bd.Location((31,-23,11),(23,17,31))
    file=out/"nested-export.glb"
    custom=export_glb(outer,file)
    loaded=three_read([file])[0]
    node_error=bound_error(bounds(outer),loaded["bbox_mm"])
    parser_error=bound_error(custom,loaded["bbox_mm"])
    assert node_error<2e-5 and parser_error<2e-5
    surface_error=max(bd.Vertex(*v).distance_to(outer) for v in loaded["surface_samples_mm"])
    assert surface_error<2e-5
    return {"three_bbox_error_mm":node_error,"parser_vs_three_error_mm":parser_error,
        "three_surface_sample_error_mm":surface_error,"file_sha256":sha(file),
        "source_bbox_mm":bounds(outer),"loaded_bbox_mm":loaded["bbox_mm"]}

def main():
    out=ROOT/"artifacts/p2"
    sets=[review_set(p) for p in ("artifacts/baseline","artifacts/variants/wall_thickness",
                                 "artifacts/variants/pcb_support_height")]
    result={"review":"P2 direct file review", "model_provenance":"User confirmed Astra/High; runtime model not independently readable",
        "sets":sets,"nested_export":nested_export(out),"independent_cad_app":"unverified",
        "passed":True,"source_hashes":{str(p.relative_to(ROOT)).replace('\\','/'):sha(p)
            for p in [*sorted((ROOT/"cad").glob("*.py")),ROOT/"cad/parameters.json",
                      ROOT/"tests/test_geometry.py",Path(__file__),ROOT/"scripts/review_glb_three.mjs"]}}
    (out/"astra-file-review.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"passed":True,"sets":len(sets),"nested_export":result["nested_export"]},indent=2))

if __name__=="__main__":
    main()
