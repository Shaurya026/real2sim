import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {ObjectControls} from './object-controls.js';
const $=id=>document.getElementById(id);
const state={ready:false,error:null,playing:false,time:0,duration:0,walk:false,cutaway:false};
window.sceneExample={state};
try{
 const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,1.75));renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;$('viewport').appendChild(renderer.domElement);
 const scene=new THREE.Scene();scene.background=new THREE.Color('#141e25');scene.add(new THREE.HemisphereLight(0xffffff,0x65747c,2));const sun=new THREE.DirectionalLight(0xffffff,2);sun.position.set(3,7,4);scene.add(sun);
 const camera=new THREE.PerspectiveCamera(55,innerWidth/innerHeight,.005,100),controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
 const sceneId=document.body.dataset.scene||'yellow_room';const specs=await (await fetch('../interaction-specs.json')).json();const sceneSpec=specs[sceneId];
 const response=await fetch('room.glb');if(!response.ok)throw Error(`Scene asset returned HTTP ${response.status}`);
 const bytes=await response.arrayBuffer(),manifest=await (await fetch('../original-assets.json')).json(),record=manifest.assets.find(a=>a.path===sceneSpec.asset);
 if(!record)throw Error('Missing original asset provenance');
 if(crypto.subtle){const hash=await crypto.subtle.digest('SHA-256',bytes),hex=Array.from(new Uint8Array(hash),b=>b.toString(16).padStart(2,'0')).join('');if(hex!==record.sha256)throw Error('Original scene hash mismatch');state.hashVerified=true;}
 const gltf=await new GLTFLoader().parseAsync(bytes,new URL('.',location.href).href);const root=gltf.scene;scene.add(root);root.updateMatrixWorld(true);
 const bounds=new THREE.Box3().setFromObject(root),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3()),radius=Math.max(size.length(),.1);
 camera.far=radius*50;camera.updateProjectionMatrix();controls.maxDistance=radius*8;controls.minDistance=.03;
 const walls=[];root.traverse(o=>{if(o.isMesh&&/^(ceiling|entrance_glass|entrance_upper|left_wall|right_upper)$/.test(o.name))walls.push(o);});
 function cutaway(value){state.cutaway=value;for(const wall of walls)wall.visible=!value;$('cutaway').setAttribute('aria-pressed',String(value));}
 function exitWalk(){state.walk=false;controls.enabled=true;$('walk').setAttribute('aria-pressed','false');}
 function interior(){exitWalk();cutaway(false);camera.position.set(center.x,bounds.min.y+size.y*.59,bounds.max.z-size.z*.08);controls.target.set(center.x,bounds.min.y+size.y*.47,bounds.min.z+size.z*.22);controls.update();}
 function overview(){exitWalk();cutaway(true);controls.target.copy(center);camera.position.copy(center).add(new THREE.Vector3(1,.7,1.4).normalize().multiplyScalar(radius*.9));controls.update();}
 let objectEditor;
 const mixer=new THREE.AnimationMixer(root);let action,clips=gltf.animations,selected=0;
 if(!clips.length)throw Error('Original chair animation is missing');
 function poseAt(t){state.time=Math.max(0,Math.min(t,state.duration));action.reset();action.setLoop(THREE.LoopOnce,1);action.clampWhenFinished=true;action.play();mixer.setTime(state.time);root.updateMatrixWorld(true);if(objectEditor)objectEditor.sync();$('timeline').value=String(state.time);$('time-label').textContent=`Timeline · ${state.time.toFixed(1)} / ${state.duration.toFixed(1)} s`;}
 function choose(i){mixer.stopAllAction();selected=i;action=mixer.clipAction(clips[i]);state.duration=clips[i].duration;state.playing=false;$('play').textContent='Play';$('timeline').max=String(state.duration);poseAt(0);}
 $('clip').replaceChildren(...clips.map((c,i)=>new Option(c.name||`Animation ${i+1}`,String(i))));$('clip').disabled=false;$('clip').onchange=e=>choose(Number(e.target.value));
 for(const id of ['play','reset','timeline'])$(id).disabled=false;
 $('play').onclick=()=>{if(state.time>=state.duration)poseAt(0);state.playing=!state.playing;$('play').textContent=state.playing?'Pause':'Play';};
 $('reset').onclick=()=>{state.playing=false;$('play').textContent='Play';poseAt(0);};
 $('timeline').oninput=e=>{state.playing=false;$('play').textContent='Play';poseAt(Number(e.target.value));};
 $('cutaway').onclick=()=>cutaway(!state.cutaway);$('interior').onclick=interior;$('overview').onclick=overview;
 const keys=new Set();$('walk').onclick=()=>{state.walk=!state.walk;controls.enabled=!state.walk;$('walk').setAttribute('aria-pressed',String(state.walk));};
 window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName))return;if(e.code==='Escape'){exitWalk();keys.clear();return;}if(state.walk&&['KeyW','KeyA','KeyS','KeyD','KeyQ','KeyE','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.code)){e.preventDefault();keys.add(e.code);}});
 window.addEventListener('keyup',e=>keys.delete(e.code));window.addEventListener('blur',()=>keys.clear());
 let dragging=false;renderer.domElement.addEventListener('pointerdown',e=>{if(!state.walk)return;dragging=true;renderer.domElement.setPointerCapture(e.pointerId);});renderer.domElement.addEventListener('pointerup',()=>dragging=false);renderer.domElement.addEventListener('pointercancel',()=>dragging=false);
 renderer.domElement.addEventListener('pointermove',e=>{if(!state.walk||!dragging)return;const rot=new THREE.Euler().setFromQuaternion(camera.quaternion,'YXZ');rot.y-=e.movementX*.003;rot.x=THREE.MathUtils.clamp(rot.x-e.movementY*.003,-1.5,1.5);camera.quaternion.setFromEuler(rot);});
 choose(0);interior();
 objectEditor=new ObjectControls({root,scene,camera,controls,renderer,objects:sceneSpec.objects,onSelect:exitWalk,beforeEdit:()=>{state.playing=false;$('play').textContent='Play';if(state.time>0)poseAt(0);}});window.sceneExample.objectEditor=objectEditor;
 state.ready=true;$('status').textContent=`Original scene loaded · ${clips.length} original animation · scale unverified`;
 window.sceneExample.setTime=poseAt;window.sceneExample.snapshot=()=>{root.updateMatrixWorld(true);const seat=root.getObjectByName('office_chair_seat');return {time:state.time,clip:selected,seat:seat?Array.from(seat.matrixWorld.elements):null,camera:camera.position.toArray()};};
 let previous=performance.now();const direction=new THREE.Vector3();
 renderer.setAnimationLoop(now=>{const dt=Math.min((now-previous)/1000,.05);previous=now;
  if(state.playing){poseAt(state.time+dt);if(state.time>=state.duration){state.playing=false;$('play').textContent='Play';}}
  if(state.walk){const down=(...codes)=>codes.some(c=>keys.has(c));direction.set((down('KeyD','ArrowRight')?1:0)-(down('KeyA','ArrowLeft')?1:0),0,(down('KeyS','ArrowDown')?1:0)-(down('KeyW','ArrowUp')?1:0)).applyQuaternion(camera.quaternion);direction.y+=(keys.has('KeyE')?1:0)-(keys.has('KeyQ')?1:0);if(direction.lengthSq())camera.position.addScaledVector(direction.normalize(),dt*.7);controls.target.copy(camera.position).add(new THREE.Vector3(0,0,-1).applyQuaternion(camera.quaternion));}else controls.update();
  renderer.render(scene,camera);
 });
 addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);});
}catch(error){state.error=String(error.message||error);$('error').hidden=false;$('error').textContent=`The scene could not load: ${state.error}. Serve this folder over HTTP, or download the GLB to inspect it locally.`;$('status').textContent='Loading failed';console.error(error);}
