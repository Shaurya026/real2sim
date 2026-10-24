import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {GaussianLayer} from './gaussians.js';
import {permittedMove} from './interaction.js';
import {attachInteractiveNode} from './node-objects.js';
const $=s=>document.querySelector(s), status=$('#status');
const state={ready:false,objects:[],selected:null,walk:false,keys:new Set(),errors:[],cameraViews:[],manifest:null};
window.room2sim={state};
const renderer=new THREE.WebGLRenderer({antialias:false,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;$('#viewport').appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#18212a');
scene.add(new THREE.HemisphereLight(0xffffff,0x4b535b,2));
const sun=new THREE.DirectionalLight(0xffffff,2);sun.position.set(4,7,3);scene.add(sun);
const camera=new THREE.PerspectiveCamera(60,innerWidth/innerHeight,.01,500);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
const layer=new GaussianLayer(scene,renderer),loader=new GLTFLoader(),roomRoot=new THREE.Group(),repairRoot=new THREE.Group();scene.add(roomRoot,repairRoot);
const boundsRoot=new THREE.Group();boundsRoot.visible=false;scene.add(boundsRoot);
const grid=new THREE.GridHelper(10,20,0x4a6275,0x2a3f4d);scene.add(grid);
let manifest,roomMesh,walkingDrag=false,previous=performance.now();
const v=new THREE.Vector3(),q=new THREE.Quaternion();
function apply(root,t){root.position.fromArray(t.position);root.quaternion.fromArray(t.quaternion);root.scale.setScalar(t.scale);root.updateMatrixWorld(true);}
function snapshot(root){return {position:root.position.toArray(),quaternion:root.quaternion.toArray(),scale:root.scale.x};}
function save(blob,name){const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function home(){const c=manifest.camera;camera.up.fromArray(c.up||[0,1,0]);camera.position.fromArray(c.position);controls.target.fromArray(c.target);camera.lookAt(...c.target);controls.update();}
async function meshAsset(url){return (await loader.loadAsync(url)).scene;}
function select(id){state.selected=state.objects.find(o=>o.spec.id===id)||null;$('#objects').value=id||'';
 const s=state.selected;$('#object-info').textContent=s?`${s.spec.label||s.spec.id} · ${s.spec.background_removed?'background separated':'background removal unverified'} · ${s.spec.representation}`:'';
 for(const id of ['left','right','forward','back','lift','lower','turn'])$('#'+id).disabled=!s;
}
function updateBounds(){for(const o of state.objects){o.root.updateWorldMatrix(true,false);
 const c=new THREE.Vector3().fromArray(o.spec.collider.center||[0,0,0]).applyMatrix4(o.root.matrixWorld);
 const d=new THREE.Vector3().fromArray(o.spec.collider.dimensions).multiplyScalar(o.root.getWorldScale(new THREE.Vector3()).x);
 // Enclose rotated local box in a world AABB.
 const rot=new THREE.Matrix3().setFromMatrix4(new THREE.Matrix4().makeRotationFromQuaternion(o.root.getWorldQuaternion(new THREE.Quaternion()))).elements;
 const dims=[0,1,2].map(i=>Math.abs(rot[i])*d.x+Math.abs(rot[i+3])*d.y+Math.abs(rot[i+6])*d.z);
 o.worldBounds={center:c.toArray(),dimensions:dims};o.helper.position.copy(c);o.helper.scale.fromArray(dims);
}}
function move(id,delta,yaw=0){select(id);const o=state.selected;if(!o)return false;
 const before=snapshot(o.root);o.root.position.add(new THREE.Vector3(...delta));o.root.rotateY(yaw);updateBounds();
 const obstacles=(manifest.colliders||[]).map(c=>({min:c.min,max:c.max}));
 for(const other of state.objects){if(other!==o){const b=other.worldBounds;obstacles.push({min:b.center.map((x,i)=>x-b.dimensions[i]/2),max:b.center.map((x,i)=>x+b.dimensions[i]/2)});}}
 const b=o.worldBounds;if(!permittedMove(b.center,b.dimensions,obstacles)){apply(o.root,before);updateBounds();status.textContent='Movement blocked by an interaction bound';return false;}
 layer.dirty=true;status.textContent=`Moved ${o.spec.label||id} · kinematic preview`;return true;
}
try{
 const response=await fetch('./scene.json');if(!response.ok)throw Error('Missing scene.json');manifest=await response.json();state.manifest=manifest;
 $('#title').textContent=manifest.title;document.title=manifest.title+' · Room2Sim';
 $('#scope').textContent=`${manifest.world.metric_scale_verified?'Measured scale':'Scale unverified'} · ${manifest.world.units} · no policy training`;
 $('#provenance').textContent=JSON.stringify(manifest.provenance,null,2);
 $('#limitations').textContent=(manifest.limitations||[]).join(' · ');
 apply(roomRoot,manifest.room.transform);home();
 status.textContent='Loading room assets…';
 if(manifest.room.representation==='splat')await layer.add(manifest.room.asset,roomRoot);
 else if(manifest.room.asset){roomMesh=await meshAsset(manifest.room.asset);roomRoot.add(roomMesh);}
 if(manifest.room.mesh)repairRoot.add(await meshAsset(manifest.room.mesh));
 if(manifest.camera_views){const poses=await fetch(manifest.camera_views);state.cameraViews=await poses.json();}
 for(const spec of manifest.objects||[]){
  let root;
  if(spec.node){
   root=attachInteractiveNode(scene,roomMesh,repairRoot,spec);
  }else{
   root=new THREE.Group();scene.add(root);apply(root,spec.transform);
   if(spec.representation==='splat')await layer.add(spec.asset,root);
   else if(spec.representation==='mesh')root.add(await meshAsset(spec.asset));
   else if(spec.representation==='primitive'){
    const c=spec.collider;const box=new THREE.Mesh(new THREE.BoxGeometry(...c.dimensions),new THREE.MeshStandardMaterial({color:spec.color||'#de9d58'}));box.position.fromArray(c.center||[0,0,0]);root.add(box);
   }else throw Error('Unsupported object representation');
  }
  const helper=new THREE.Mesh(new THREE.BoxGeometry(1,1,1),new THREE.MeshBasicMaterial({color:'#85ddc3',wireframe:true,depthTest:false}));boundsRoot.add(helper);
  state.objects.push({spec,root,helper,initial:snapshot(root)});
  const option=document.createElement('option');option.value=spec.id;option.textContent=spec.label||spec.id;$('#objects').appendChild(option);
 }
 updateBounds();select(state.objects[0]?.spec.id||'');grid.visible=manifest.show_grid!==false;
 $('#show-room').onchange=e=>{roomRoot.visible=e.target.checked;layer.dirty=true;};$('#show-repairs').onchange=e=>repairRoot.visible=e.target.checked;
 $('#show-colliders').onchange=e=>boundsRoot.visible=e.target.checked;
 $('#home').onclick=home;$('#objects').onchange=e=>select(e.target.value);
 const step=manifest.interaction_step||.05;
 for(const [id,delta] of [['left',[-step,0,0]],['right',[step,0,0]],['forward',[0,0,-step]],['back',[0,0,step]],['lift',[0,step*3,0]],['lower',[0,-step*3,0]]])
  $('#'+id).onclick=()=>state.selected&&move(state.selected.spec.id,delta);
 $('#turn').onclick=()=>state.selected&&move(state.selected.spec.id,[0,0,0],Math.PI/8);
 $('#reset').onclick=()=>{for(const o of state.objects)apply(o.root,o.initial);updateBounds();layer.dirty=true;status.textContent='Objects reset';};
 $('#shot').onclick=()=>renderer.domElement.toBlob(blob=>save(blob,'room-review.png'));
 $('#export').onclick=()=>save(new Blob([JSON.stringify({version:1,objects:state.objects.map(o=>({id:o.spec.id,transform:snapshot(o.root)}))},null,2)],{type:'application/json'}),'placements.json');
 $('#walk').onclick=()=>{state.walk=!state.walk;controls.enabled=!state.walk;$('#walk').textContent=state.walk?'Exit walk':'Walk mode';};
 const ray=new THREE.Raycaster(),pointer=new THREE.Vector2();let down;
 renderer.domElement.addEventListener('pointerdown',e=>{down=[e.clientX,e.clientY];walkingDrag=state.walk;});
 renderer.domElement.addEventListener('pointerup',e=>{walkingDrag=false;if(!down||Math.hypot(e.clientX-down[0],e.clientY-down[1])>5)return;
  pointer.set(e.clientX/innerWidth*2-1,-e.clientY/innerHeight*2+1);ray.setFromCamera(pointer,camera);
  // Raycast invisible box proxies, independent of Gaussian renderer internals.
  const visible=boundsRoot.visible;boundsRoot.visible=true;boundsRoot.updateMatrixWorld(true);
  const hits=ray.intersectObjects(state.objects.map(o=>o.helper));boundsRoot.visible=visible;
  if(hits.length)select(state.objects.find(o=>o.helper===hits[0].object).spec.id);
 });
 renderer.domElement.addEventListener('pointermove',e=>{if(!walkingDrag)return;const euler=new THREE.Euler().setFromQuaternion(camera.quaternion,'YXZ');euler.y-=e.movementX*.003;euler.x=Math.max(-1.5,Math.min(1.5,euler.x-e.movementY*.003));camera.quaternion.setFromEuler(euler);});
 window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(document.activeElement.tagName))return;state.keys.add(e.code);if(e.code==='Escape'){state.walk=false;controls.enabled=true;$('#walk').textContent='Walk mode';}});
 window.addEventListener('keyup',e=>state.keys.delete(e.code));window.addEventListener('blur',()=>state.keys.clear());
 window.room2sim.move=move;window.room2sim.home=home;
 window.room2sim.setCamera=view=>{camera.position.fromArray(view.position);camera.up.fromArray(view.up||[0,1,0]);controls.target.fromArray(view.target);camera.lookAt(...view.target);controls.update();layer.lastView='';};
 window.room2sim.snapshot=()=>state.objects.map(o=>({id:o.spec.id,transform:snapshot(o.root)}));
 state.ready=true;status.textContent=`Ready · ${layer.sources.reduce((n,s)=>n+s.data.count,0).toLocaleString()} Gaussians · SH degree 0 review`;
 $('#badge').textContent=manifest.room.representation==='splat'?'Gaussian environment · editable objects':'Archive mesh environment · editable objects';
}catch(error){state.errors.push(error.message);$('#error').hidden=false;$('#error').textContent='Scene could not load: '+error.message;status.textContent='Loading failed';console.error(error);}
renderer.setAnimationLoop(time=>{
 const dt=Math.min(.05,(time-previous)/1000);previous=time;
 if(state.walk){
  const k=state.keys;const forward=(k.has('KeyW')?1:0)-(k.has('KeyS')?1:0),right=(k.has('KeyD')?1:0)-(k.has('KeyA')?1:0),up=(k.has('KeyE')?1:0)-(k.has('KeyQ')?1:0);
  v.set(right,0,-forward).applyQuaternion(camera.quaternion);v.y+=up;camera.position.addScaledVector(v,dt*1.2);
 }else controls.update();
 layer.update(camera,time);renderer.render(scene,camera);
});
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
