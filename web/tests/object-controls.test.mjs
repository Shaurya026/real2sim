import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as THREE from '../../docs/mesh/vendor/three.module.js';
import {ObjectControls} from '../../docs/mesh/object-controls.js';
function fixture(){
 const elements=new Map(),previousDocument=globalThis.document,previousOption=globalThis.Option;
 globalThis.document={getElementById:id=>{if(!elements.has(id))elements.set(id,{hidden:false,textContent:'',replaceChildren(){},setAttribute(){}});return elements.get(id);}};
 globalThis.Option=class{constructor(label,value){this.label=label;this.value=value;}};
 const scene=new THREE.Scene(),root=new THREE.Group(),source=new THREE.Group();source.rotation.x=-Math.PI/2;root.add(source);scene.add(root);
 // Exercise the actual original bottle triangles, not a replacement primitive.
 const raw=fs.readFileSync(new URL('../../docs/mesh/environment/assets/room.glb',import.meta.url)),jsonSize=raw.readUInt32LE(12),doc=JSON.parse(raw.subarray(20,20+jsonSize).toString()),binary=20+jsonSize+8;
 const node=doc.nodes.find(n=>n.name==='bottle_31'),primitive=doc.meshes[node.mesh].primitives[0],a=doc.accessors[primitive.attributes.POSITION],view=doc.bufferViews[a.bufferView],offset=binary+(view.byteOffset||0)+(a.byteOffset||0);
 const positions=new Float32Array(a.count*3);for(let i=0;i<positions.length;i++)positions[i]=raw.readFloatLE(offset+i*4);
 const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(positions,3));
 if(primitive.indices!==undefined){const index=doc.accessors[primitive.indices],iv=doc.bufferViews[index.bufferView],start=binary+(iv.byteOffset||0)+(index.byteOffset||0),width=index.componentType===5125?4:2;geometry.setIndex(Array.from({length:index.count},(_,i)=>width===4?raw.readUInt32LE(start+i*width):raw.readUInt16LE(start+i*width)));}
 const bottle=new THREE.Mesh(geometry,new THREE.MeshBasicMaterial({side:THREE.DoubleSide}));bottle.name='bottle_31';source.add(bottle);
 const left=new THREE.Mesh(new THREE.BoxGeometry(.1,.1,.1),new THREE.MeshBasicMaterial()),right=left.clone();left.name='left';right.name='right';left.position.x=-.3;right.position.x=.3;source.add(left,right);
 const camera=new THREE.PerspectiveCamera(50,4/3,.01,100),canvas={addEventListener(){},removeEventListener(){},getBoundingClientRect(){return {left:0,top:0,width:800,height:600};}};
 const controls={target:new THREE.Vector3(),update(){}};
 const editor=new ObjectControls({root,scene,camera,controls,renderer:{domElement:canvas},objects:[{id:'bottle',label:'Bottle',names:['bottle_31']},{id:'chair',label:'Chair assembly',names:['left','right']}]});
 return {editor,source,bottle,left,right,camera,root,clean(){editor.destroy();globalThis.document=previousDocument;globalThis.Option=previousOption;}};
}
test('bottle world-space lift respects the original Z-up root and resets exactly',()=>{
 const f=fixture();try{
  const before=f.bottle.getWorldPosition(new THREE.Vector3()),snapshot=f.editor.snapshot();f.editor.move([0,.08,0]);
  const after=f.bottle.getWorldPosition(new THREE.Vector3());assert.ok(Math.abs(after.y-before.y-.08)<1e-9);assert.ok(Math.abs(after.z-before.z)<1e-9);
  f.editor.reset();assert.deepEqual(f.editor.snapshot(),snapshot);
 }finally{f.clean();}
});
test('object focus restores hidden bottle geometry and frames its actual bounds',()=>{
 const f=fixture();try{
  f.bottle.visible=false;f.source.visible=false;f.editor.select('bottle',true);assert.equal(f.bottle.visible,true);assert.equal(f.source.visible,true);
  const center=f.editor.box().getCenter(new THREE.Vector3());assert.ok(f.camera.position.distanceTo(center)>0);assert.ok(f.camera.position.toArray().every(Number.isFinite));
  const direction=f.camera.getWorldDirection(new THREE.Vector3());assert.ok(direction.dot(center.clone().sub(f.camera.position).normalize())>.999);
  f.editor.isolate(true);assert.equal(f.bottle.visible,true);assert.equal(f.left.visible,false);f.editor.isolate(false);assert.equal(f.left.visible,true);
 }finally{f.clean();}
});
test('turning a multipart chair preserves assembly spacing and reset restores every part',()=>{
 const f=fixture();try{
  f.editor.select('chair');const initial=f.editor.snapshot(),distance=f.left.getWorldPosition(new THREE.Vector3()).distanceTo(f.right.getWorldPosition(new THREE.Vector3()));
  f.editor.turn(Math.PI/2);const rotated=f.left.getWorldPosition(new THREE.Vector3()).distanceTo(f.right.getWorldPosition(new THREE.Vector3()));
  assert.ok(Math.abs(rotated-distance)<1e-9);assert.notDeepEqual(f.editor.snapshot(),initial);f.editor.reset();assert.deepEqual(f.editor.snapshot(),initial);
 }finally{f.clean();}
});
test('pointer picking selects the visible bottle mesh',()=>{
 const f=fixture();try{
  f.editor.select('bottle',true);f.camera.updateMatrixWorld(true);f.editor.select('chair');
  f.editor.pointerDown({clientX:400,clientY:300});f.editor.pointerUp({clientX:400,clientY:300,button:0});assert.equal(f.editor.selected.id,'bottle');
 }finally{f.clean();}
});
