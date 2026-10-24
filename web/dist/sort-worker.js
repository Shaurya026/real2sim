self.onmessage=({data})=>{
 const {positions,matrix:m,generation}=data;
 const count=positions.length/3,depth=new Float32Array(count),order=new Uint32Array(count);
 for(let i=0;i<count;i++){order[i]=i;depth[i]=m[2]*positions[i*3]+m[6]*positions[i*3+1]+m[10]*positions[i*3+2]+m[14];}
 order.sort((a,b)=>depth[a]-depth[b]);
 self.postMessage({order,generation},[order.buffer]);
};
