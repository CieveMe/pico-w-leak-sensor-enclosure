import { Vector3 } from 'three';

/** Manifest explosion offsets and parent positions are both CAD millimetres. */
export function explodedPosition(basePosition, offsetMm, amount) {
  return basePosition.clone().addScaledVector(offsetMm, amount);
}

/** Three.js ray intersections include descendants of invisible groups. */
export function isEffectivelyVisible(object, root) {
  for (let current = object; current; current = current.parent) {
    if (current.visible === false) return false;
    if (current === root) return true;
  }
  return false;
}
