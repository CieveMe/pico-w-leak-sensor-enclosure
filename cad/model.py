"""Four printable solids with attributed hardware/service keep-outs."""
from dataclasses import dataclass
from math import radians, tan, sin, cos
from .runtime import bd

@dataclass
class Assembly:
    parts: dict
    references: dict
    keepouts: dict
    interfaces: dict
    values: dict

def box(x,y,z,lo):
    return bd.Pos(*lo)*bd.Box(x,y,z,align=(bd.Align.MIN,)*3)

def cylinder(d,height,x,y,z):
    return bd.Pos(x,y,z)*bd.Cylinder(d/2,height,align=(bd.Align.CENTER,bd.Align.CENTER,bd.Align.MIN))

def union(shapes):
    result=shapes[0]
    for s in shapes[1:]:
        result=result+s
    return result

def build_assembly(p,pcb_shift=(0,0,0)):
    w,l,t,f,h=(p[k] for k in ("shell_width","shell_length","wall_thickness","floor_thickness","shell_height"))
    zpcb=f+p["pcb_support_height"]
    px,py=p["pcb_hole_pitch_x"]/2,p["pcb_hole_pitch_y"]/2
    lid_xy=[(sx*p["lid_screw_x"],sy*p["lid_screw_y"]) for sx in (-1,1) for sy in (-1,1)]
    joint_xy=[(sx*p["bracket_joint_x"],sy*p["bracket_joint_y"]) for sx in (-1,1) for sy in (-1,1)]
    wall_xy=[(sx*p["wall_screw_x"],sy*p["wall_screw_y"]) for sx in (-1,1) for sy in (-1,1)]
    a=p["antenna_window_width"]/2
    antenna=box(2*a,p["antenna_window_end_y"]+60,80,(-a,-60,-20))
    lower=box(w,l,h,(-w/2,-l/2,0))-box(w-2*t,l-2*t,h,(-w/2+t,-l/2+t,f))
    posts=[cylinder(p["pcb_post_diameter"],p["pcb_support_height"]+.2,x,py,f-.2) for x in (-px,px)]
    pads=[box(3,8,p["pcb_support_height"]+.2,(x,-4,f-.2)) for x in (-11.5,8.5)]
    bosses=[cylinder(p["lid_boss_diameter"],h-f+.2,x,y,f-.2) for x,y in lid_xy]
    lower=union([lower,*posts,*pads,*bosses])
    for x in (-px,px):
        lower=lower-cylinder(p["pcb_pilot_diameter"],h,x,py,f-1.5)
    for x,y in lid_xy:
        lower=lower-cylinder(p["lid_pilot_diameter"],h,x,y,f+.5)
    for x,y in joint_xy:
        lower=lower-cylinder(p["lid_hole_diameter"],f+1,x,y,-.5)
    socket=box(p["usb_socket_width"],p["usb_socket_end_y"]-p["usb_socket_start_y"],
               p["usb_socket_height"],(-p["usb_socket_width"]/2,p["usb_socket_start_y"],zpcb+1))
    usb=box(p["usb_plug_width"],p["usb_path_end_y"]-p["usb_path_start_y"],
            p["usb_plug_height"],(-p["usb_plug_width"]/2,p["usb_path_start_y"],zpcb+.5))
    lower=lower-box(p["usb_opening_width"],20,p["usb_opening_height"],
                    (-p["usb_opening_width"]/2,l/2-t-1,zpcb+3.5-p["usb_opening_height"]/2))-antenna
    lower=lower-box(20,p["cable_opening_width"],p["cable_opening_height"],
                    (w/2-t-1,6-p["cable_opening_width"]/2,zpcb+2.5-p["cable_opening_height"]/2))
    for y in (-1,13):
        lower=lower-box(20,1.5,2,(w/2-t-1,y-.75,zpcb+1.5))
    cable=box(34,3,3,(10.5,4.5,zpcb+1))
    lid=box(w,l,p["lid_thickness"],(-w/2,-l/2,h))-antenna
    for x,y in lid_xy:
        lid=lid-cylinder(p["lid_hole_diameter"],p["lid_thickness"]+1,x,y,h-.5)
    bw,bl,bt,bz=(p[k] for k in ("bracket_width","bracket_length","bracket_thickness","bracket_top_z"))
    bracket=box(bw,bl,bt,(-bw/2,-bl/2,bz-bt))
    bracket=union([bracket,*[cylinder(7,-bz+.2,x,y,bz-.2) for x,y in joint_xy]])
    for x,y in joint_xy:
        bracket=bracket-cylinder(p["bracket_pilot_diameter"],-bz+1.5,x,y,bz-1)
    for x,y in wall_xy:
        bracket=bracket-cylinder(p["wall_hole_diameter"],bt+1,x,y,bz-bt-.5)
    bracket=bracket-antenna
    pcb=box(p["pcb_width"],p["pcb_length"],p["pcb_thickness"],
            (-p["pcb_width"]/2,-p["pcb_length"]/2,zpcb))
    for x in (-px,px):
        for y in (-py,py):
            pcb=pcb-cylinder(p["pcb_hole_diameter"],2,x,y,zpcb-.5)
    components=box(18,36,p["pcb_component_height"],(-9,-17,zpcb+p["pcb_thickness"]))
    solder=box(16,35,p["pcb_solder_height"],(-8,-15,zpcb-p["pcb_solder_height"]))
    shift=bd.Pos(*pcb_shift)
    pcb,components,solder,socket=(shift*s for s in (pcb,components,solder,socket))
    pico=bd.Compound(children=[pcb,components,socket,solder],label="pico_w_simplified")
    # 6 mm is the complete envelope, never a guessed PCB thickness.
    sx,fy,fz=p["sensor_center_x"],p["sensor_front_y"],p["sensor_front_z"]
    tilt=p["sensor_tilt_degrees"]
    sensor_transform=bd.Pos(sx,fy,fz)*bd.Rot(tilt,0,0)
    sensor=sensor_transform*box(p["sensor_width"],p["sensor_length"],p["sensor_height"],
                               (-p["sensor_width"]/2,0,0))
    active=sensor_transform*box(16,20,8,(-8,0,-1))
    connector=sensor_transform*box(16,8,10,(-8,22,0))
    # For this convex planar envelope, every upward-facing face contributes to
    # the vertical sweep. Top-face-only extrusion misses the inclined rear face.
    removal=union([sensor,*[bd.extrude(face,amount=25,dir=(0,0,1))
                           for face in sensor.faces() if face.normal_at().Z>1e-9]])
    def rail(x,width,lift):
        y0,y1=-18,17
        z0,z1=fz+(y0-fy)*tan(radians(tilt))+lift,fz+(y1-fy)*tan(radians(tilt))+lift
        sketch=bd.Plane.YZ*bd.Polygon((y0,0),(y1,0),(y1,z1),(y0,z0),align=None)
        return bd.Pos(sx+x,0,0)*bd.extrude(sketch,amount=width)
    half=p["sensor_width"]/2
    gap=p["sensor_side_clearance"]
    rails=[rail(-half-gap,2.4,0),rail(half-1,2.4,0),
           rail(-half-gap-2.4,2.4,6),rail(half+gap,2.4,6)]
    front=box(2*(half+gap+2.4),1.2,2.2,(sx-half-gap-2.4,-18,0))
    rear=box(2*(half+gap+2.4),2,2.2,(sx-half-gap-2.4,15,0))
    # Edge stops catch gravity-driven downslope travel while leaving the
    # assumed central active area and the full vertical removal sweep open.
    stop_end=fy-p["sensor_height"]*sin(radians(tilt))-gap
    stops=[box(2.4,1.2,fz+p["sensor_height"],(sx+x,stop_end-1.2,0))
           for x in (-half-gap,half-1)]
    holder=union([*rails,front,rear,*stops])
    downslope=bd.Pos(0,-3*cos(radians(tilt)),-3*sin(radians(tilt)))*sensor
    parts=dict(lower_shell=lower,lid=lid,wall_bracket=bracket,probe_holder=holder)
    for key,s in parts.items(): s.label=key
    keepouts=dict(pcb=pcb,components=components,solder=solder,usb_socket=socket,
                  usb_insertion=usb,cable_route=cable,antenna=antenna,
                  sensor_body=sensor,sensor_active=active,sensor_connector=connector,sensor_removal=removal,
                  sensor_left_guide=rails[2],sensor_right_guide=rails[3],sensor_downslope=downslope)
    interfaces=dict(pcb_holes=[(x,y) for x in (-px,px) for y in (-py,py)],
                    pcb_used_holes=[(-px,py),(px,py)],lid_holes=lid_xy,
                    bracket_holes=joint_xy,wall_holes=wall_xy,pcb_bottom=zpcb,
                    contact_descriptions=["shell rim / lid underside at Z=shell_height",
                      "shell underside / bracket post tops at Z=0",
                      "PCB underside / front posts and mid-edge pads",
                      "sensor underside / inclined edge rails"])
    pico.label="pico_w";sensor.label="water_sensor"
    return Assembly(parts,dict(pico_w=pico,water_sensor=sensor),keepouts,interfaces,p)
