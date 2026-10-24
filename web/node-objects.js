// Resolve repaired props as well as archive nodes, retaining their authored pose.
export function attachInteractiveNode(scene,room,repairs,spec){
 const roots=spec.node_source==='repairs'?[repairs]:spec.node_source==='room'?[room]:[room,repairs];
 if(spec.node_source&&!['room','repairs'].includes(spec.node_source))throw Error('Unknown interactive node source');
 const matches=[];
 for(const root of roots)root?.traverse(node=>{if(node.name===spec.node)matches.push(node);});
 if(matches.length!==1)throw Error(`Expected one interactive node: ${spec.node}; found ${matches.length}`);
 const node=matches[0];
 scene.updateMatrixWorld(true);
 scene.attach(node);
 // Repair specs use browser/world transforms; exported placement edits override
 // the original GLB pose. Legacy archive nodes retain their source transforms.
 if(spec.node_source==='repairs'){
  node.position.fromArray(spec.transform.position);
  node.quaternion.fromArray(spec.transform.quaternion);
  node.scale.setScalar(spec.transform.scale);
  node.updateMatrixWorld(true);
 }
 return node;
}
