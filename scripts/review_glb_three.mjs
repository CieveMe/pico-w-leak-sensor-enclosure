// Independent P2 scene measurement using the same standard loader as the viewer.
import fs from 'node:fs';
import path from 'node:path';
import { Group, Vector3 } from '../viewer/node_modules/three/build/three.module.js';
import { GLTFLoader } from '../viewer/node_modules/three/examples/jsm/loaders/GLTFLoader.js';

const files = process.argv.slice(2);
if (!files.length) throw new Error('Pass one or more GLB paths');
const results = [];
for (const file of files) {
  const bytes = fs.readFileSync(file);
  const data = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const gltf = await new GLTFLoader().parseAsync(data, '');
  const frame = new Group();
  frame.scale.setScalar(1000);
  frame.rotation.x = Math.PI / 2;
  frame.add(gltf.scene);
  frame.updateMatrixWorld(true);
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  let count = 0;
  const samples = [];
  gltf.scene.traverse(obj => {
    const pos = obj.geometry?.getAttribute('position');
    if (!pos) return;
    for (let i = 0; i < pos.count; i++) {
      const v = new Vector3().fromBufferAttribute(pos, i).applyMatrix4(obj.matrixWorld).toArray();
      for (let axis = 0; axis < 3; axis++) {
        min[axis] = Math.min(min[axis], v[axis]);
        max[axis] = Math.max(max[axis], v[axis]);
      }
      if (i % Math.max(1, Math.floor(pos.count / 12)) === 0) samples.push(v);
      count++;
    }
  });
  if (!count) throw new Error('No scene vertices: ' + file);
  results.push({file: path.basename(file), bbox_mm: {min, max}, vertex_count: count, surface_samples_mm: samples});
}
process.stdout.write(JSON.stringify({reader: 'Three.js GLTFLoader 0.180.0', results}, null, 2));
