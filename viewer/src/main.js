import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { toCadCoordinates } from './cad-transform.js';
import { explodedPosition, isEffectivelyVisible } from './scene-utils.js';
import './style.css';

const $ = (selector) => document.querySelector(selector);
const wrap = $('#canvas-wrap');
const loader = $('#load-state');
const scene = new THREE.Scene();
scene.background = new THREE.Color('#eeede6');
const camera = new THREE.PerspectiveCamera(34, 1, 0.05, 12000);
camera.up.set(0, 0, 1);
camera.position.set(190, -250, 165);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.domElement.setAttribute('aria-label', '可旋转缩放的CAD装配视图');
wrap.prepend(renderer.domElement);

scene.add(new THREE.HemisphereLight(0xf6f3e9, 0x66756e, 2.0));
const key = new THREE.DirectionalLight(0xfff8e9, 2.6);
key.position.set(-120, -170, 240); key.castShadow = true;
key.shadow.mapSize.set(1024, 1024); key.shadow.camera.left = -140; key.shadow.camera.right = 140;
key.shadow.camera.top = 140; key.shadow.camera.bottom = -140; scene.add(key);
const fill = new THREE.DirectionalLight(0xd7e2ef, 1.0); fill.position.set(140, 80, 110); scene.add(fill);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(5000, 5000), new THREE.ShadowMaterial({ opacity: 0.12 }));
floor.position.z = -7.7; floor.receiveShadow = true; scene.add(floor);

const cadRoot = new THREE.Group(); scene.add(cadRoot);
const axes = new THREE.Group();
const axisMaterial = [0xc9644e, 0x598667, 0x587ba0].map(color => new THREE.LineBasicMaterial({ color }));
[[new THREE.Vector3(-18,0,0),new THREE.Vector3(18,0,0)],
 [new THREE.Vector3(0,-18,0),new THREE.Vector3(0,18,0)],
 [new THREE.Vector3(0,0,-18),new THREE.Vector3(0,0,18)]].forEach((points,index)=>axes.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(points),axisMaterial[index])));
scene.add(axes);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true; controls.dampingFactor = 0.075; controls.screenSpacePanning = false;
controls.target.set(25, -12, 5); controls.minDistance = 55; controls.maxDistance = 1600; controls.update();

let manifest; let checks=[]; let selectedId; let loadedParts=[];
const loader3d = new GLTFLoader();
const originalMaterials = new WeakMap();
const roleNames = { custom: '自设计零件', reference: '简化参考包络' };
const failureRows = [];

function colorOf(hex) { return new THREE.Color(hex); }
function formatMM(value) { return Number(value).toFixed(value % 1 === 0 ? 0 : 2).replace(/\.00$/, ''); }
function dimensions(entry) { return entry.bbox.max.map((v,i)=>v-entry.bbox.min[i]); }
function fileUrl(path) { return `/artifacts/baseline/${path}`; }
function downloadLink(path,label) {
  const a=document.createElement('a');a.href=fileUrl(path);a.download=path.split('/').pop();a.textContent=label;return a;
}
function setPartInfo(entry) {
  selectedId=entry.id;
  $('#part-name').textContent=entry.name;
  $('#part-role').textContent=`${roleNames[entry.role] ?? entry.role} · ${entry.id}`;
  $('#part-index').textContent=String(manifest.parts.indexOf(entry)+1).padStart(2,'0');
  const d=dimensions(entry);
  $('#part-size').textContent=`${formatMM(d[0])} × ${formatMM(d[1])} × ${formatMM(d[2])}`;
  $('#part-bbox').textContent=`X ${formatMM(entry.bbox.min[0])}…${formatMM(entry.bbox.max[0])}  /  Y ${formatMM(entry.bbox.min[1])}…${formatMM(entry.bbox.max[1])}  /  Z ${formatMM(entry.bbox.min[2])}…${formatMM(entry.bbox.max[2])}`;
  const links=$('#part-links');links.replaceChildren();
  for(const fmt of ['step','stl','glb']) if(entry.files[fmt]) links.append(downloadLink(entry.files[fmt],fmt.toUpperCase()));
  for(const button of document.querySelectorAll('.part-chip')) button.setAttribute('aria-pressed',String(button.dataset.part===selectedId));
  for(const item of loadedParts) item.scene.traverse(o=>{if(!o.isMesh)return;const mats=Array.isArray(o.material)?o.material:[o.material];for(const mat of mats){const old=originalMaterials.get(mat);if(!old)continue;if(mat.emissive){mat.emissive.set(selectedId===item.entry.id?'#b87940':old.emissive);mat.emissiveIntensity=selectedId===item.entry.id ? 0.16 : old.emissiveIntensity;}}});
}
function makePartEntry(entry) {
  const label=document.createElement('label');label.className='part-chip';label.dataset.part=entry.id;
  const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=true;checkbox.setAttribute('aria-label',`显示${entry.name}`);
  const swatch=document.createElement('i');swatch.className='swatch';swatch.style.background=entry.color;
  const name=document.createElement('span');name.textContent=entry.name;
  label.append(checkbox,swatch,name);label.setAttribute('aria-pressed','false');
  label.addEventListener('click',event=>{if(event.target!==checkbox)setPartInfo(entry);});
  checkbox.addEventListener('change',()=>{const item=loadedParts.find(x=>x.entry.id===entry.id);if(item)item.scene.visible=checkbox.checked;});
  $('#part-strip').append(label);
}
function loadPart(entry) {
  return new Promise((resolve,reject)=>loader3d.load(fileUrl(entry.files.glb),gltf=>{
    const cadScene=toCadCoordinates(gltf.scene);
    const origin=cadScene.position.clone();
    cadScene.traverse(object=>{if(!object.isMesh)return;object.castShadow=true;object.receiveShadow=true;object.userData.partId=entry.id;
      const apply=material=>{const clone=material.clone();clone.color.copy(colorOf(entry.color));clone.roughness=.72;clone.metalness=.015;if(clone.emissive){originalMaterials.set(clone,{emissive:clone.emissive.clone(),emissiveIntensity:clone.emissiveIntensity});clone.emissive.set(selectedId===entry.id?'#b87940':'#000000');clone.emissiveIntensity=selectedId===entry.id ? 0.16 : 0;}return clone;};
      object.material=Array.isArray(object.material)?object.material.map(apply):apply(object.material);
    });
    cadRoot.add(cadScene);const item={entry,scene:cadScene,basePosition:origin};loadedParts.push(item);
    cadScene.userData.explodeVector=new THREE.Vector3(...entry.explode);
    makePartEntry(entry);resolve();
  },undefined,reject));
}
function setValidation(report) {
  checks=report.checks ?? [];
  const passed=checks.filter(c=>c.status==='passed').length;
  const failed=checks.filter(c=>c.status==='failed');
  const unverified=checks.filter(c=>c.status==='unverified');
  $('#validation-counts').textContent=`${passed} 通过　${failed.length} 失败　${unverified.length} 待验证`;
  const chip=$('#validation-state');
  if(failed.length){chip.textContent='有失败';chip.className='status-chip has-fail';}
  else if(unverified.length){chip.textContent='含待验证';chip.className='status-chip has-unverified';}
  else{chip.textContent='数字检查通过';chip.className='status-chip';}
  const notes=[];
  if(failed.length)notes.push(`失败：${failed.slice(0,2).map(r=>r.name).join('、')}`);
  if(unverified.length)notes.push(`待验证：${unverified.map(r=>r.name).join('、')}`);
  $('#validation-note').textContent=notes.length?notes.join('；'):'所有数字检查均已通过。';
}
function makeDownloads() {
  const list=$('#download-list');list.replaceChildren();
  const items=[['assembly.step','总装 STEP'],['validation.json','数字检查报告'],['parameters.json','本版参数'],['../drawings/pico-w-dimensions.svg','尺寸图 SVG']];
  for(const [file,label] of items){const a=document.createElement('a');a.className='file-link';a.href=file.startsWith('../')?'/drawings/pico-w-dimensions.svg':fileUrl(file);a.download=file.split('/').pop();a.innerHTML=`<span>${label}</span><small>${file.split('/').pop()}</small>`;list.append(a);}
  $('#revision').textContent=`REV ${manifest.source_revision.slice(7,19)} · ${manifest.variant}`;
}
function fitView() {
  const box=new THREE.Box3().setFromObject(cadRoot);if(box.isEmpty())return;
  const size=box.getSize(new THREE.Vector3());const center=box.getCenter(new THREE.Vector3());
  controls.target.copy(center);const radius=Math.max(size.x,size.y,size.z,30);camera.position.copy(center).add(new THREE.Vector3(1.08,-1.55,1.05).normalize().multiplyScalar(radius*2.35));
  camera.near=Math.max(.05,radius/3000);camera.far=radius*30;camera.updateProjectionMatrix();controls.update();
}
$('#explode').addEventListener('input',event=>{const amount=Number(event.target.value);$('#explode-value').value=`${Math.round(amount*100)}%`;for(const item of loadedParts)item.scene.position.copy(explodedPosition(item.basePosition,item.scene.userData.explodeVector,amount));});
$('#transparency').addEventListener('click',event=>{const button=event.currentTarget;const show=button.getAttribute('aria-pressed')!=='true';button.setAttribute('aria-pressed',String(show));for(const item of loadedParts)if(['lower_shell','lid'].includes(item.entry.id))item.scene.traverse(o=>{if(!o.isMesh)return;for(const mat of (Array.isArray(o.material)?o.material:[o.material])){mat.transparent=show;mat.opacity=show ? 0.24 : 1;mat.depthWrite=!show;} });});
$('#fit-view').addEventListener('click',fitView);$('#reset-view').addEventListener('click',()=>{camera.position.set(190,-250,165);controls.target.set(25,-12,5);controls.update();});
function visibleIntersection(raycaster) {
  return raycaster.intersectObjects(cadRoot.children,true).find(hit=>isEffectivelyVisible(hit.object,cadRoot));
}
if(import.meta.env.DEV){
  Object.defineProperty(window,'__picoCadReview',{configurable:false,value:Object.freeze({
    parts:()=>loadedParts.map(({entry,scene,basePosition})=>({id:entry.id,base:basePosition.toArray(),position:scene.position.toArray(),explode:scene.userData.explodeVector.toArray(),visible:isEffectivelyVisible(scene,cadRoot)})),
    pickRay:(origin,direction)=>{const ray=new THREE.Raycaster(new THREE.Vector3(...origin),new THREE.Vector3(...direction).normalize());return visibleIntersection(ray)?.object.userData.partId??null;}
  })});
}
let pointerStart=null;
renderer.domElement.addEventListener('pointerdown',e=>pointerStart=[e.clientX,e.clientY]);
renderer.domElement.addEventListener('pointerup',e=>{
  if(!pointerStart||Math.hypot(e.clientX-pointerStart[0],e.clientY-pointerStart[1])>4)return;
  pointerStart=null;
  const rect=renderer.domElement.getBoundingClientRect();
  const pointer=new THREE.Vector2((e.clientX-rect.left)/rect.width*2-1,-(e.clientY-rect.top)/rect.height*2+1);
  const ray=new THREE.Raycaster();ray.setFromCamera(pointer,camera);
  const hit=visibleIntersection(ray);
  if(hit){const id=hit.object.userData.partId;const entry=manifest.parts.find(p=>p.id===id);if(entry)setPartInfo(entry);}
});

function resize(){const width=wrap.clientWidth,height=wrap.clientHeight;if(!width||!height)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(wrap);resize();
async function start(){
  try{
    const [manifestResponse,validationResponse]=await Promise.all([fetch('/artifacts/baseline/manifest.json'),fetch('/artifacts/baseline/validation.json')]);
    if(!manifestResponse.ok||!validationResponse.ok)throw new Error('同版manifest或validation.json未找到');
    manifest=await manifestResponse.json();const report=await validationResponse.json();
    if(manifest.validation_sha256&&report.source_revision!==manifest.source_revision)throw new Error('manifest与检查报告版本不一致');
    if(manifest.units!=='mm'||manifest.cad_up_axis!=='Z'||manifest.glb_units!=='m'||manifest.up_axis!=='Y')throw new Error('模型单位或坐标轴契约不符');
    setValidation(report);makeDownloads();
    const results=await Promise.allSettled(manifest.parts.map(loadPart));
    const rejected=results.filter(x=>x.status==='rejected');if(rejected.length)throw new Error(`${rejected.length}个零件GLB加载失败`);
    if(loadedParts.length!==manifest.parts.length)throw new Error('零件数量与manifest不一致');
    loader.classList.add('hidden');setPartInfo(manifest.parts[0]);fitView();
  }catch(error){loader.textContent=`加载失败：${error.message}`;loader.style.color='#a34c35';$('#validation-state').textContent='报告不可用';$('#validation-state').className='status-chip has-fail';console.error(error);}
}
start();
function animate(){requestAnimationFrame(animate);controls.update();renderer.render(scene,camera);}animate();
