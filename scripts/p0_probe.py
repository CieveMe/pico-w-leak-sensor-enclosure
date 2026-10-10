"""P0 export and coordinate probe with process-scoped Windows font workaround."""
from __future__ import annotations
import json, struct, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cad.runtime import bd
print("Compatibility: project-scoped import; see cad/runtime.py")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "p0"
OUT.mkdir(parents=True, exist_ok=True)
box = bd.Box(20, 12, 8)
probe = bd.Pos(11, -17, 4) * bd.Box(12, 7, 5, align=(bd.Align.MIN, bd.Align.MIN, bd.Align.MIN))
def bbox(shape):
    b=shape.bounding_box(); return [[b.min.X,b.min.Y,b.min.Z],[b.max.X,b.max.Y,b.max.Z]]
def volume(shape): return sum(s.volume for s in shape.solids())
def read_glb(path):
    data=path.read_bytes(); magic,version,total=struct.unpack_from('<4sII',data,0)
    if magic!=b'glTF' or version!=2 or total!=len(data): raise ValueError('Invalid GLB header')
    chunks=[]; offset=12
    while offset<len(data):
        size,kind=struct.unpack_from('<I4s',data,offset); chunks.append([kind,data[offset+8:offset+8+size]]); offset+=8+size
    doc=next((json.loads(c.decode('utf-8')) for k,c in chunks if k==b'JSON'),None)
    if doc is None or not any(k==b'BIN\x00' for k,_ in chunks): raise ValueError('GLB missing JSON or binary chunk')
    return doc,chunks

def write_glb(path,doc,chunks):
    encoded=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8'); encoded+=b' '*((-len(encoded))%4)
    parts=[]
    for kind,payload in chunks:
        if kind==b'JSON': payload=encoded
        payload+=b'\x00'*((-len(payload))%4)
        parts.append(struct.pack('<I4s',len(payload),kind)+payload)
    body=b''.join(parts); path.write_bytes(struct.pack('<4sII',b'glTF',2,12+len(body))+body)

def correct_root_translation(path):
    """Apply build123d's missing world-basis conversion to root translations only."""
    doc,chunks=read_glb(path)
    scene=doc.get('scenes',[{}])[doc.get('scene',0)]
    changed=[]
    for i in scene.get('nodes',[]):
        node=doc['nodes'][i]
        if 'translation' in node:
            x,y,z=node['translation']; node['translation']=[x,z,-y]; changed.append(i)
    write_glb(path,doc,chunks)
    return changed

def export_pair(shape,name):
    step=OUT/f'{name}.step'; raw=OUT/f'{name}-build123d-raw.glb'; final=OUT/f'{name}.glb'
    before=(str(shape.location),bbox(shape),volume(shape))
    if not bd.export_step(shape,step,unit=bd.Unit.MM): raise RuntimeError('STEP export failed')
    if not bd.export_gltf(shape,raw,unit=bd.Unit.MM,binary=True): raise RuntimeError('GLB export failed')
    after=(str(shape.location),bbox(shape),volume(shape))
    unchanged=(before==after)
    if not unchanged: raise RuntimeError(f'export_gltf mutated source shape: before={before} after={after}')
    doc,chunks=read_glb(raw)
    final.write_bytes(raw.read_bytes())
    roots=doc.get('scenes',[{}])[doc.get('scene',0)].get('nodes',[])
    changed=[]
    for i in roots:
        node=doc['nodes'][i]
        if 'translation' in node:
            x,y,z=node['translation']; node['translation']=[x,z,-y]; changed.append(i)
    write_glb(final,doc,chunks)
    return step,raw,final,bd.import_step(step),changed,unchanged

def positions_world(path):
    doc,chunks=read_glb(path); binary=next(payload for kind,payload in chunks if kind==b'BIN\x00')
    ident=((1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)); positions=[]
    def mul(a,b): return tuple(tuple(sum(a[r][k]*b[k][c] for k in range(4)) for c in range(4)) for r in range(4))
    def matrix(n):
        if 'matrix' in n:
            m=n['matrix']; return tuple(tuple(m[c*4+r] for c in range(4)) for r in range(4))
        t=n.get('translation',[0,0,0]); s=n.get('scale',[1,1,1]); x,y,z,w=n.get('rotation',[0,0,0,1])
        rot=((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0),(2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0),(2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0),(0,0,0,1))
        return mul(((1,0,0,t[0]),(0,1,0,t[1]),(0,0,1,t[2]),(0,0,0,1)),
                   mul(rot,((s[0],0,0,0),(0,s[1],0,0),(0,0,s[2],0),(0,0,0,1))))
    def visit(i,parent):
        n=doc['nodes'][i]; world=mul(parent,matrix(n))
        if 'mesh' in n:
            for prim in doc['meshes'][n['mesh']]['primitives']:
                acc=doc['accessors'][prim['attributes']['POSITION']]; view=doc['bufferViews'][acc['bufferView']]
                if acc['componentType']!=5126 or acc['type']!='VEC3': raise ValueError('Unsupported POSITION encoding')
                start=view.get('byteOffset',0)+acc.get('byteOffset',0); stride=view.get('byteStride',12)
                for j in range(acc['count']):
                    xyz=struct.unpack_from('<3f',binary,start+j*stride); v=(*xyz,1)
                    positions.append([sum(world[r][c]*v[c] for c in range(4)) for r in range(3)])
        for child in n.get('children',[]): visit(child,world)
    scene=doc.get('scenes',[{'nodes':list(range(len(doc.get('nodes',[]))))}])[doc.get('scene',0)]
    for i in scene.get('nodes',[]): visit(i,ident)
    if not positions: raise ValueError('GLB contains no world-space mesh vertices')
    return doc,positions

def extents(points): return [[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
def near(a,b,tol=2e-5): return abs(a-b)<=tol
def glb_probe(raw,final):
    raw_doc,raw_pts=positions_world(raw); doc,pts=positions_world(final)
    raw_bbox=extents(raw_pts); final_bbox=extents(pts)
    cad=bbox(probe)
    restored=[[p[0]*1000,-p[2]*1000,p[1]*1000] for p in pts]
    restored_bbox=extents(restored); expected=[[cad[0][i],cad[1][i]] for i in range(3)]
    raw_nodes=raw_doc['nodes']; root_ids=raw_doc.get('scenes',[{}])[raw_doc.get('scene',0)].get('nodes',[])
    raw_translations=[raw_nodes[i].get('translation') for i in root_ids]
    return {'cad_bbox_mm':cad,'raw_build123d_world_vertex_bbox_m':raw_bbox,'raw_root_translations_m':raw_translations,
            'normalized_glb_world_vertex_bbox_m':final_bbox,'viewer_transform':{'scale':1000,'rotation_x_degrees':90,'formula_mm':'(1000*x_glb, -1000*z_glb, 1000*y_glb)'},
            'viewer_restored_bbox_mm':restored_bbox,'expected_cad_bbox_mm':expected,
            'viewer_restored_bbox_matches_cad':all(near(restored_bbox[i][j],expected[i][j]) for i in range(3) for j in range(2)),
            'vertex_count':len(pts),'glb_version':doc.get('asset',{}).get('version')}

results={}
for name,shape in (('box',box),('asymmetric_off_origin',probe)):
    step,raw,glb,reopened,changed,source_unchanged=export_pair(shape,name)
    b0,b1=bbox(shape),bbox(reopened); v0,v1=volume(shape),volume(reopened)
    step_ok=(len(shape.solids())==len(reopened.solids()) and all(abs(b0[i][j]-b1[i][j])<=.01 for i in range(2) for j in range(3)) and abs(v0-v1)/v0<=1e-5)
    results[name]={'source_bbox_mm':b0,'step_reimport_bbox_mm':b1,'source_volume_mm3':v0,'step_reimport_volume_mm3':v1,
                   'source_solid_count':len(shape.solids()),'step_reimport_solid_count':len(reopened.solids()),'step_reimport_pass':step_ok,
                   'step_file':step.name,'build123d_raw_glb_file':raw.name,'viewer_glb_file':glb.name,'normalized_root_nodes':changed,'export_gltf_source_geometry_unchanged':source_unchanged}
results['asymmetric_off_origin']['glb_coordinate_probe']=glb_probe(OUT/'asymmetric_off_origin-build123d-raw.glb',OUT/'asymmetric_off_origin.glb')
coord=results['asymmetric_off_origin']['glb_coordinate_probe']
report={'stage':'P0','build123d_version':bd.__version__,'model_provenance':'Model is not inferred by this script; see STATUS.md' ,
'units':'CAD mm; measured GLB mesh world coordinates in m','cad_up_axis':'Z','build123d_glb_local_mesh_axis':'Y-up after Rx(-90 degrees)',
'exporter_source_behavior':'build123d.export_gltf applies Rx(-90) and uses Unit.MM. Measured raw world coordinates show it leaves root node translation in the original XYZ basis. The viewer GLB normalizes root translations into glTF basis.',
'font_compatibility':'process-scoped glob filter excludes only confirmed malformed %WINDIR%/Fonts/mstmc.ttf during build123d import; no font parse exceptions are caught.',
'tolerances':{'step_bbox_mm':.01,'step_relative_volume':1e-5,'glb_coordinate_mm':2e-5},'cases':results,
'all_checks_pass':all(x['step_reimport_pass'] for x in results.values()) and coord['viewer_restored_bbox_matches_cad']}
(OUT/'p0-coordinate-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
if not report['all_checks_pass']: raise SystemExit('P0 failed; inspect retained raw export and report')
