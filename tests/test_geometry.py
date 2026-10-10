"""Independent witnesses for exports, parameter effects and deliberate errors."""
import json
import subprocess
import sys
import struct
from pathlib import Path
import numpy as np
import pytest
from cad.config import load_parameters
from cad.model import build_assembly,box
from cad.runtime import bd
from cad.validate import geometry_checks,intersection_volume
from cad.build import generate,bbox_error,source_revision
from cad.export import export_glb,bbox
from cad.gltf import node_matrix,world_vertices

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/"artifacts"/"p2"
EVIDENCE.mkdir(parents=True,exist_ok=True)

def save(name,data):
    (EVIDENCE/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

@pytest.fixture(scope="module")
def baseline(tmp_path_factory):
    report,a=generate(tmp_path_factory.mktemp("baseline"))
    assert report["digital_checks_pass"],[r for r in report["checks"] if r["status"]=="failed"]
    return report,a

def test_baseline_export_and_true_reimport(baseline):
    report,a=baseline
    names={r["name"] for r in report["checks"] if r["status"]=="passed"}
    assert {"step.bbox_max_error","step.relative_volume_error","glb.world_bbox_max_error",
            "assembly.component_bbox","assembly.component_volume","assembly.step_mm_unit"}<=names
    assert report["unverified_count"]==1
    save("baseline-test-witness.json",{"digital_checks_pass":True,"source_revision":report["source_revision"],
         "check_count":report["check_count"],"independent_app":"unverified"})

@pytest.mark.parametrize("name,value",[
    ("wall_thickness",2.0),("pcb_support_height",6.0)])
def test_meaningful_variants_regenerate(name,value,baseline,tmp_path):
    base_report,base=baseline
    report,variant=generate(tmp_path/name,{name:value},name)
    assert report["digital_checks_pass"],[r for r in report["checks"] if r["status"]=="failed"]
    if name=="wall_thickness":
        old=next(r["measured"] for r in base_report["checks"] if r["name"]=="dimension.inner_wall_x")
        new=next(r["measured"] for r in report["checks"] if r["name"]=="dimension.inner_wall_x")
        assert new-old==pytest.approx(.5)
        assert variant.parts["lower_shell"].volume<base.parts["lower_shell"].volume
        witness={"old_inner_wall_x_mm":old,"new_inner_wall_x_mm":new,
                 "old_volume_mm3":base.parts["lower_shell"].volume,"new_volume_mm3":variant.parts["lower_shell"].volume}
    else:
        old=bbox(base.keepouts["pcb"])["min"][2];new=bbox(variant.keepouts["pcb"])["min"][2]
        assert new-old==pytest.approx(2)
        witness={"old_pcb_bottom_mm":old,"new_pcb_bottom_mm":new}
    save("variant-"+name+".json",{"source_revision":report["source_revision"],"digital_checks_pass":True,
         "parameter":name,"new_value":value,"witness":witness,"check_count":report["check_count"]})

@pytest.mark.parametrize("name,value",[
    ("wall_thickness",0),("minimum_air_clearance",-.1)])
def test_invalid_parameters_fail_nonzero_cli(name,value,tmp_path):
    output=tmp_path/name
    process=subprocess.run([sys.executable,str(ROOT/"cad"/"build.py"),"--output",str(output),
                            "--set",f"{name}={value}"],cwd=ROOT,capture_output=True,text=True)
    assert process.returncode!=0
    report=json.loads((output/"validation.json").read_text())
    assert report["digital_checks_pass"] is False
    assert name in report["error"]
    assert not (output/"manifest.json").exists()
    save("negative-"+name+".json",{"parameter":name,"bad_value":value,"expected_failure_caught":True,
         "exit_code":process.returncode,"actual_report":report})

@pytest.mark.parametrize("kind",["moved_pcb","small_usb"])
def test_deliberate_geometric_invasion_is_caught(kind):
    data,p=load_parameters(overrides={"usb_opening_width":6} if kind=="small_usb" else None)
    assembly=build_assembly(p,(12,0,0) if kind=="moved_pcb" else (0,0,0))
    checks=geometry_checks(assembly,data)
    expected="pcb" if kind=="moved_pcb" else "usb_insertion"
    hits=[r for r in checks.rows if r["name"]=="host_keepout.overlap" and
          r["objects"]==[expected,"lower_shell"] and r["status"]=="failed"]
    assert hits and hits[0]["measured"]>1e-6
    save("negative-"+kind+".json",{"expected_failure_caught":True,"source_revision":source_revision(data),
         "deliberate_change":"PCB +12 mm X" if kind=="moved_pcb" else "USB opening width 6 mm",
         "expected_failing_objects":[expected,"lower_shell"],"specific_hits":hits,
         "all_checks":checks.rows})

def test_off_origin_arbitrary_rotation_export(tmp_path):
    shape=bd.Pos(11,-17,4)*bd.Rot(17,31,23)*box(12,7,5,(0,0,0))
    target=tmp_path/"orientation.glb"
    source=bbox(shape);actual=export_glb(shape,target)
    error=bbox_error(source,actual)
    assert error<2e-5
    save("orientation-probe.json",{"source_bbox_mm":source,"glb_world_restored_bbox_mm":actual,
         "maximum_error_mm":error,"threshold_mm":2e-5,"passed":True,
         "source_rotation_deg":[17,31,23],"source_translation_mm":[11,-17,4],
         "method":"copy location conjugation before exporter post-Rx(-90)"})

def test_gltf_trs_order_nonuniform_scale():
    n={"translation":[1,2,3],"rotation":[0,0,np.sin(np.pi/4),np.cos(np.pi/4)],"scale":[2,3,4]}
    actual=node_matrix(n)@np.array([1,1,1,1])
    assert actual==pytest.approx([-2,4,7,1])

def _write_single_vertex_glb(path, nodes, scene_roots, vertex=(1.0,1.0,1.0)):
    binary=struct.pack("<3f",*vertex)
    document={"asset":{"version":"2.0"},"scene":0,
        "scenes":[{"nodes":scene_roots}],"nodes":nodes,
        "meshes":[{"primitives":[{"attributes":{"POSITION":0},"mode":0}]}],
        "accessors":[{"bufferView":0,"componentType":5126,"count":1,"type":"VEC3",
                      "min":list(vertex),"max":list(vertex)}],
        "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":12}],
        "buffers":[{"byteLength":12}]}
    encoded=json.dumps(document,separators=(",",":")).encode("utf-8")
    encoded+=b" "*((4-len(encoded)%4)%4)
    binary+=b"\0"*((4-len(binary)%4)%4)
    total=12+8+len(encoded)+8+len(binary)
    path.write_bytes(struct.pack("<4sII",b"glTF",2,total)+
        struct.pack("<I4s",len(encoded),b"JSON")+encoded+
        struct.pack("<I4s",len(binary),b"BIN\0")+binary)

def test_gltf_nested_world_transform_trs_rotation_and_nonuniform_scale(tmp_path):
    # Child vertex -> child S/R/T -> parent S/R/T must yield [7, 0, 3].
    path=tmp_path/"nested.glb"
    root={"translation":[10,2,0],"rotation":[0,0,np.sin(np.pi/4),np.cos(np.pi/4)],
          "scale":[2,1,1],"children":[1]}
    child={"translation":[1,2,0],"rotation":[0,0,np.sin(np.pi/4),np.cos(np.pi/4)],
           "scale":[1,2,3],"mesh":0}
    _write_single_vertex_glb(path,[root,child],[0])
    np.testing.assert_allclose(world_vertices(path),[[7,0,3]],atol=1e-12,rtol=0)

def test_gltf_explicit_matrix_is_column_major(tmp_path):
    # Column-major translation (4, -2, 3) plus a 90-degree Z rotation.
    matrix=[0,1,0,0, -1,0,0,0, 0,0,1,0, 4,-2,3,1]
    path=tmp_path/"matrix.glb"
    _write_single_vertex_glb(path,[{"matrix":matrix,"mesh":0}],[0])
    np.testing.assert_allclose(world_vertices(path),[[3,-1,4]],atol=1e-12,rtol=0)

@pytest.mark.parametrize("bad",["wall_thickness=oops","wall_thickness"])
def test_malformed_override_removes_previous_healthy_manifest(bad,tmp_path):
    output=tmp_path/"reused-output"
    output.mkdir()
    (output/"manifest.json").write_text('{"previous":"healthy"}',encoding="utf-8")
    process=subprocess.run([sys.executable,"-X","utf8",str(ROOT/"cad/build.py"),
        "--output",str(output),"--set",bad],cwd=ROOT,capture_output=True,encoding="utf-8")
    assert process.returncode==1
    assert not (output/"manifest.json").exists()
    assert json.loads((output/"validation.json").read_text())["digital_checks_pass"] is False

@pytest.mark.parametrize("angle",[0,12,20])
def test_sensor_removal_contains_translated_body_at_path_extremes_and_midpoint(angle):
    _,p=load_parameters(overrides={"sensor_tilt_degrees":angle})
    assembly=build_assembly(p)
    for lift in (0,2,10,25):
        missing=bd.Pos(0,0,lift)*assembly.keepouts["sensor_body"]-assembly.keepouts["sensor_removal"]
        assert sum(s.volume for s in missing.solids())<1e-6

def test_rear_removal_obstacle_is_detected(baseline):
    from dataclasses import replace
    _,assembly=baseline
    data,_=load_parameters()
    # In the raised rear-face strip omitted by the previous top-only sweep.
    blocker=box(.2,.2,.2,(64.9,13.7,20))
    assert intersection_volume(blocker,assembly.keepouts["sensor_body"])<1e-6
    modified=replace(assembly,parts={**assembly.parts,
        "probe_holder":assembly.parts["probe_holder"]+blocker})
    row=next(r for r in geometry_checks(modified,data).rows
        if r["name"]=="external_sensor.overlap" and r["objects"]==["probe_holder","sensor_removal"])
    assert row["status"]=="failed" and row["measured"]>.007

def test_missing_edge_stops_fail_retention_check(baseline):
    from dataclasses import replace
    _,assembly=baseline
    data,_=load_parameters()
    # Remove the front strip containing both stops and keep the other parts.
    stripped=assembly.parts["probe_holder"]-box(40,10,30,(45,-25,0))
    modified=replace(assembly,parts={**assembly.parts,"probe_holder":stripped})
    row=next(r for r in geometry_checks(modified,data).rows if r["name"]=="sensor.downslope_stop")
    assert row["status"]=="failed" and row["measured"]<1e-6
