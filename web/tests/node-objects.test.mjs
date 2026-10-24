import test from 'node:test';
import assert from 'node:assert/strict';
import * as THREE from '../../docs/mesh/vendor/three.module.js';
import {attachInteractiveNode} from '../node-objects.js';

test('repaired prop is selected from repair layer and uses exported world placement',()=>{
 const scene=new THREE.Scene(),room=new THREE.Group(),repairs=new THREE.Group(),parent=new THREE.Group(),box=new THREE.Mesh(new THREE.BoxGeometry(.2,.4,.3));
 parent.rotation.x=-Math.PI/2;parent.position.set(9,4,3);parent.name='replacement';parent.add(box);repairs.add(parent);scene.add(room,repairs);
 const root=attachInteractiveNode(scene,room,repairs,{node:'replacement',node_source:'repairs',transform:{position:[1,2,3],quaternion:[0,0,0,1],scale:.5}});
 assert.equal(root,parent);assert.equal(root.parent,scene);assert.deepEqual(root.position.toArray(),[1,2,3]);assert.equal(root.scale.x,.5);
 assert.equal(root.children[0],box);const initial=root.position.clone();root.position.y+=.15;root.position.copy(initial);assert.deepEqual(root.position.toArray(),[1,2,3]);
});
test('legacy room node retains its original world transform through axis conversion',()=>{
 const scene=new THREE.Scene(),room=new THREE.Group(),repairs=new THREE.Group(),bottle=new THREE.Mesh(new THREE.BoxGeometry(.1,.1,.3));
 room.rotation.x=-Math.PI/2;bottle.position.set(1,2,3);bottle.name='bottle';room.add(bottle);scene.add(room,repairs);scene.updateMatrixWorld(true);
 const before=bottle.matrixWorld.clone();attachInteractiveNode(scene,room,repairs,{node:'bottle'});scene.updateMatrixWorld(true);
 for(let i=0;i<16;i++)assert.ok(Math.abs(before.elements[i]-bottle.matrixWorld.elements[i])<1e-10);
});
test('missing, ambiguous and unknown node sources fail visibly',()=>{
 const scene=new THREE.Scene(),room=new THREE.Group(),repairs=new THREE.Group();scene.add(room,repairs);
 assert.throws(()=>attachInteractiveNode(scene,room,repairs,{node:'missing'}),/found 0/);
 for(const root of [room,repairs]){const node=new THREE.Group();node.name='same';root.add(node);}
 assert.throws(()=>attachInteractiveNode(scene,room,repairs,{node:'same'}),/found 2/);
 assert.throws(()=>attachInteractiveNode(scene,room,repairs,{node:'same',node_source:'other'}),/Unknown/);
});
