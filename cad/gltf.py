"""GLB inspection in scene world coordinates, not bare mesh POSITION space."""
import json
import struct
import numpy as np

def read_glb(path):
    data=path.read_bytes()
    magic,version,size=struct.unpack_from("<4sII",data,0)
    if magic!=b"glTF" or version!=2 or size!=len(data): raise ValueError("Invalid GLB header")
    chunks=[];i=12
    while i<len(data):
        n,k=struct.unpack_from("<I4s",data,i)
        chunks.append((k,data[i+8:i+8+n]));i+=8+n
    doc=json.loads(next(v for k,v in chunks if k==b"JSON").decode("utf-8"))
    binary=next(v for k,v in chunks if k==b"BIN\0")
    return doc,binary

def node_matrix(n):
    if "matrix" in n: return np.array(n["matrix"],dtype=float).reshape((4,4),order="F")
    x,y,z,w=n.get("rotation",[0,0,0,1])
    r=np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],
                [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],
                [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1]])
    scale=np.diag([*n.get("scale",[1,1,1]),1])
    translation=np.eye(4);translation[:3,3]=n.get("translation",[0,0,0])
    return translation@r@scale

def world_vertices(path):
    doc,binary=read_glb(path)
    points=[]
    def visit(i,parent):
        n=doc["nodes"][i];matrix=parent@node_matrix(n)
        if "mesh" in n:
            for prim in doc["meshes"][n["mesh"]]["primitives"]:
                acc=doc["accessors"][prim["attributes"]["POSITION"]]
                if acc["componentType"]!=5126 or acc["type"]!="VEC3" or "sparse" in acc:
                    raise ValueError("Unsupported POSITION encoding")
                view=doc["bufferViews"][acc["bufferView"]]
                if view.get("buffer",0)!=0: raise ValueError("External GLB buffer")
                start=view.get("byteOffset",0)+acc.get("byteOffset",0);stride=view.get("byteStride",12)
                xyz=np.array([struct.unpack_from("<3f",binary,start+j*stride) for j in range(acc["count"])])
                hom=np.column_stack((xyz,np.ones(len(xyz))))
                points.extend((matrix@hom.T).T[:,:3].tolist())
        for child in n.get("children",[]): visit(child,matrix)
    for i in doc["scenes"][doc.get("scene",0)].get("nodes",[]): visit(i,np.eye(4))
    if not points: raise ValueError("No world-space mesh vertices")
    return np.array(points)

def cad_bbox(path):
    pts=world_vertices(path)
    restored=np.column_stack((pts[:,0]*1000,-pts[:,2]*1000,pts[:,1]*1000))
    return {"min":restored.min(axis=0).tolist(),"max":restored.max(axis=0).tolist()}
