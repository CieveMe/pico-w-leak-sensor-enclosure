import assert from 'node:assert/strict';
import test from 'node:test';
import { Vector3 } from 'three';
import { explodedPosition, isEffectivelyVisible } from '../src/scene-utils.js';

test('manifest millimetre explosion vector scales linearly at 0, 50, and 100 percent', () => {
  const base = new Vector3(0, 0, 18);
  const offset = new Vector3(0, 0, 35);
  assert.deepEqual(explodedPosition(base, offset, 0).toArray(), [0, 0, 18]);
  assert.deepEqual(explodedPosition(base, offset, 0.5).toArray(), [0, 0, 35.5]);
  assert.deepEqual(explodedPosition(base, offset, 1).toArray(), [0, 0, 53]);
});

test('hidden parent groups suppress descendant picking', () => {
  const root = { visible: true, parent: null };
  const visiblePart = { visible: true, parent: root };
  const hiddenPart = { visible: true, parent: root };
  const hiddenMesh = { visible: true, parent: hiddenPart };
  assert.equal(isEffectivelyVisible(visiblePart, root), true);
  hiddenPart.visible = false;
  assert.equal(isEffectivelyVisible(hiddenMesh, root), false);
  hiddenPart.visible = true;
  assert.equal(isEffectivelyVisible(hiddenMesh, root), true);
});
