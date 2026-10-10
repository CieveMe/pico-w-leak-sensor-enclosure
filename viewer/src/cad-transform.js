import { Group } from 'three';
/** Single parent conversion; translations/explosion belong outside this parent in CAD mm. */
export function toCadCoordinates(gltfScene) {
  const basis = new Group();
  basis.scale.setScalar(1000);
  basis.rotation.x = Math.PI / 2;
  basis.add(gltfScene);
  basis.updateMatrixWorld(true);
  return basis;
}
