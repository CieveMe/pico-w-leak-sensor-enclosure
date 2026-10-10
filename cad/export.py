"""STEP is mm; GLB is m/Y-up with a tested world-basis adapter."""
import copy
import hashlib
from .runtime import bd
from .gltf import cad_bbox

def bbox(s):
    b=s.bounding_box()
    return {"min":[b.min.X,b.min.Y,b.min.Z],"max":[b.max.X,b.max.Y,b.max.Z]}

def export_glb(shape,path,linear=.05,angular=.1):
    # build123d 0.11.1 does location *= Rx(-90). Conjugating a COPY beforehand
    # turns that postmultiplication into the desired global premultiplication:
    # (R * L * inverse(R)) * R == R * L. Handles translation and any orientation.
    if bd.__version__!="0.11.1": raise RuntimeError("Reverify GLB adapter for build123d version")
    original=(str(shape.location),bbox(shape),shape.volume)
    cloned=copy.deepcopy(shape)
    r=bd.Location((0,0,0),(1,0,0),-90)
    inverse=bd.Location((0,0,0),(1,0,0),90)
    cloned.location=r*cloned.location*inverse
    try:
        ok=bd.export_gltf(cloned,path,unit=bd.Unit.MM,binary=True,
                         linear_deflection=linear,angular_deflection=angular)
        if not ok: raise RuntimeError("GLB exporter returned false")
    finally:
        if original!=(str(shape.location),bbox(shape),shape.volume):
            raise RuntimeError("Export mutated original CAD")
    return cad_bbox(path)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
