"""Checks measure assembled CAD, never viewer/explosion positions."""
from itertools import combinations
from .runtime import bd
from .model import box,cylinder,union
from .export import bbox
from .config import tolerance

class Checks:
    def __init__(self): self.rows=[]
    def add(self,name,objects,measured,threshold,unit,passed,detail=""):
        self.rows.append(dict(name=name,objects=objects,status="passed" if passed else "failed",
                              measured=measured,threshold=threshold,unit=unit,detail=detail))
    def le(self,name,objects,value,limit,unit,detail=""):
        self.add(name,objects,value,{"max":limit},unit,value<=limit,detail)
    def ge(self,name,objects,value,limit,unit,detail=""):
        self.add(name,objects,value,{"min":limit},unit,value>=limit,detail)
    def eq(self,name,objects,value,target,unit,detail=""):
        self.add(name,objects,value,{"expected":target},unit,value==target,detail)

def intersection_volume(a,b):
    return sum(s.volume for s in (a.intersect(b) or []))

def geometry_checks(a,data):
    c=Checks();p=a.values;eps=tolerance(data,"intersection_volume");air=p["minimum_air_clearance"]
    parts=a.parts;k=a.keepouts;z=a.interfaces["pcb_bottom"]
    for name,s in parts.items():
        c.eq("solid.valid",[name],s.is_valid,True,"boolean")
        c.eq("solid.connected_count",[name],len(s.solids()),1,"count")
        c.ge("solid.positive_volume",[name],s.volume,1e-8,"mm^3")
    for (n1,s1),(n2,s2) in combinations(parts.items(),2):
        c.le("custom_pair.overlap",[n1,n2],intersection_volume(s1,s2),eps,"mm^3",
             "All custom pairs; zero-volume contact descriptions are in manifest.")
    for obj in ("pcb","components","solder","usb_socket","usb_insertion","cable_route"):
        for host in ("lower_shell","lid","wall_bracket"):
            c.le("host_keepout.overlap",[obj,host],intersection_volume(k[obj],parts[host]),eps,"mm^3")
            if obj not in ("pcb",):
                c.ge("host_keepout.minimum_clearance",[obj,host],k[obj].distance_to(parts[host]),air,"mm")
    for host in ("lower_shell","lid","wall_bracket"):
        c.le("antenna.open_window",[host,"antenna"],intersection_volume(parts[host],k["antenna"]),eps,"mm^3",
             "Window boundary contact allowed; geometry only, not RF effectiveness.")
    core=box(14,8.5,35,(-7,-25.5,-10))
    for host in ("lower_shell","lid","wall_bracket"):
        c.ge("antenna.core_to_structure",[host,"assumed_antenna_core"],core.distance_to(parts[host]),.5,"mm",
             "Project-selected 3D check region; source 14x9 carrier cutout is not 3D certification.")
    for obj in ("sensor_body","sensor_active","sensor_connector","sensor_removal"):
        c.le("external_sensor.overlap",["probe_holder",obj],intersection_volume(parts["probe_holder"],k[obj]),eps,"mm^3",
             "Continuous vertical sweep for removal; underside contact allowed.")
    for lift in (12.5,25):
        missing=bd.Pos(0,0,lift)*k["sensor_body"]-k["sensor_removal"]
        c.le("sensor.removal_contains_lifted_body",["sensor_removal",lift],
             sum(s.volume for s in missing.solids()),eps,"mm^3",
             "Full lifted envelope must be contained, including the inclined rear face.")
    c.ge("sensor.downslope_stop",["probe_holder","sensor_downslope"],
         intersection_volume(parts["probe_holder"],k["sensor_downslope"]),.01,"mm^3",
         "A 3 mm downhill displacement must hit an edge stop; not a strength test.")
    b=bbox(k["sensor_connector"])
    c.ge("sensor.connector_elevation",["sensor_connector","front_pivot"],b["min"][2]-p["sensor_front_z"],2,"mm",
         "Assumed connector region; no waterproof or detection-depth guarantee.")
    # Air to separate guide rails is measured at actual sensor side faces.
    for guide in ("sensor_left_guide","sensor_right_guide"):
        c.ge("sensor.side_guide_clearance",["water_sensor",guide],
             k["sensor_body"].distance_to(k[guide]),air,"mm")
    for x,y in a.interfaces["pcb_holes"]:
        bore=cylinder(p["pcb_hole_diameter"],p["pcb_thickness"],x,y,z)
        c.le("pcb.manufacturer_hole_void",["pcb",x,y],intersection_volume(bore,k["pcb"]),eps,"mm^3")
        annulus=cylinder(4,p["pcb_thickness"],x,y,z)-bore
        measured=intersection_volume(annulus,k["pcb"])
        c.le("pcb.hole_surrounding_material",["pcb",x,y],abs(measured-annulus.volume),1e-5,"mm^3")
    for x,y in [(-p["pcb_hole_pitch_x"]/2+1.4,p["pcb_hole_pitch_y"]/2),
                (p["pcb_hole_pitch_x"]/2+1.4,p["pcb_hole_pitch_y"]/2),(-9.5,0),(9.5,0)]:
        point=bd.Vertex(x,y,z)
        for name,s in [("pcb",k["pcb"]),("lower_shell",parts["lower_shell"])]:
            c.le("pcb.actual_support_contact",[name,x,y],s.distance_to(point),1e-6,"mm")
    # Tool corridors encode installation order instead of global exclusions.
    tool_sets=[
        ("cover_install",a.interfaces["lid_holes"],p["shell_height"]+p["lid_thickness"],8,
         list(parts.values())+[k["pcb"],k["components"],k["usb_socket"]]),
        ("empty_shell_to_bracket",a.interfaces["bracket_holes"],p["floor_thickness"]+3,6,
         [parts["lower_shell"],parts["wall_bracket"]]),
        ("wall_bracket_first",a.interfaces["wall_holes"],p["bracket_top_z"],8,[parts["wall_bracket"]]),
    ]
    for stage,xy,z0,d,obstacles in tool_sets:
        for x,y in xy:
            tool=cylinder(d,30,x,y,z0)
            c.le("tool_access."+stage,[stage,x,y],sum(intersection_volume(tool,s) for s in obstacles),eps,"mm^3")
    for x,y in a.interfaces["pcb_used_holes"]:
        tool=union([cylinder(2.4,8,x,y,z+1),cylinder(8,20,x,y,z+9)])
        c.le("tool_access.pcb_before_cover",["PCB front screw",x,y],
             sum(intersection_volume(tool,s) for s in
                 [parts["lower_shell"],parts["wall_bracket"],k["pcb"],k["components"],k["usb_socket"]]),eps,"mm^3")
        head=cylinder(3,2,x,y,z+1)
        c.le("fastener.pcb_head_socket",["compact M2 head OD=3","usb_socket"],
             intersection_volume(head,k["usb_socket"]),eps,"mm^3")
        # Printed pilot core must exist over the actual nominal screw insertion depth.
        pilot=cylinder(p["pcb_pilot_diameter"],5,x,y,z+1-6)
        c.le("fastener.pcb_pilot_core",["lower_shell","M2x6 pilot",x,y],
             intersection_volume(pilot,parts["lower_shell"]),eps,"mm^3",
             "Pilot core only; screw thread bite intentionally not modeled.")
    for x,y in a.interfaces["lid_holes"]:
        lid_bore=cylinder(p["lid_hole_diameter"],p["lid_thickness"],x,y,p["shell_height"])
        c.le("fastener.cover_clearance_bore",["lid",x,y],intersection_volume(lid_bore,parts["lid"]),eps,"mm^3")
        tip=p["shell_height"]+p["lid_thickness"]-12
        pilot=cylinder(p["lid_pilot_diameter"],p["shell_height"]-tip,x,y,tip)
        c.le("fastener.cover_pilot_core",["lower_shell",x,y],intersection_volume(pilot,parts["lower_shell"]),eps,"mm^3")
    for x,y in a.interfaces["bracket_holes"]:
        bore=cylinder(p["lid_hole_diameter"],p["floor_thickness"],x,y,0)
        c.le("fastener.host_clearance_bore",["lower_shell",x,y],intersection_volume(bore,parts["lower_shell"]),eps,"mm^3")
        tip=p["floor_thickness"]-8
        pilot=cylinder(p["bracket_pilot_diameter"],-tip,x,y,tip)
        c.le("fastener.bracket_pilot_core",["wall_bracket",x,y],intersection_volume(pilot,parts["wall_bracket"]),eps,"mm^3")
        head=cylinder(5.5,3,x,y,p["floor_thickness"])
        c.le("fastener.host_head_pcb",["M3 host head",x,y],intersection_volume(head,k["pcb"]),eps,"mm^3")
    for x,y in a.interfaces["wall_holes"]:
        head=cylinder(7,3,x,y,p["bracket_top_z"])
        c.le("fastener.wall_head_host",["wall head","lower_shell",x,y],
             intersection_volume(head,parts["lower_shell"]),eps,"mm^3")
    # Real geometry witness for wall-thickness variants: inside wall at Y=0,Z=10.
    common=parts["lower_shell"].intersect(box(30,.2,.1,(0,-.1,10))) or []
    if not common: raise RuntimeError("No right wall in witness section")
    measured=min(s.bounding_box().min.X for s in common)
    c.add("dimension.inner_wall_x",["lower_shell"],measured,
          {"expected":p["shell_width"]/2-p["wall_thickness"],"absolute_tolerance":1e-6},"mm",
          abs(measured-(p["shell_width"]/2-p["wall_thickness"]))<1e-6)
    return c
