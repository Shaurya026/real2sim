/* Gaussian ellipses, perspective covariance projection, global CPU depth sorting.
   Deliberately uses SH degree 0. Original PLY higher-order SH remains unchanged.
   This is a review renderer, not a replacement for a CUDA evaluation renderer. */
import * as THREE from 'three';
import {parseGaussianPLY} from './ply.js';
const vertex=`
precision highp float;
attribute vec3 splatCenter;
attribute vec3 splatScale;
attribute vec4 splatQuat;
attribute vec4 splatColor;
uniform vec2 viewport;
varying vec2 gaussianUV;
varying vec4 gaussianColor;
mat3 rotation(vec4 q){
 float x=q.x,y=q.y,z=q.z,w=q.w;
 return mat3(1.-2.*(y*y+z*z),2.*(x*y+w*z),2.*(x*z-w*y),
  2.*(x*y-w*z),1.-2.*(x*x+z*z),2.*(y*z+w*x),
  2.*(x*z+w*y),2.*(y*z-w*x),1.-2.*(x*x+y*y));
}
void main(){
 vec4 c=modelViewMatrix*vec4(splatCenter,1.);
 gaussianUV=position.xy;gaussianColor=splatColor;
 if(c.z>=-0.01){gl_Position=vec4(2.,2.,2.,1.);return;}
 float d=-c.z;
 mat3 A=mat3(modelViewMatrix)*rotation(splatQuat)*mat3(splatScale.x,0.,0.,0.,splatScale.y,0.,0.,0.,splatScale.z);
 mat3 V=A*transpose(A);
 float fx=projectionMatrix[0][0]*viewport.x*.5,fy=projectionMatrix[1][1]*viewport.y*.5;
 vec3 Jx=vec3(fx/d,0.,fx*c.x/(d*d)),Jy=vec3(0.,fy/d,fy*c.y/(d*d));
 float a=dot(Jx,V*Jx)+.3,b=dot(Jx,V*Jy),e=dot(Jy,V*Jy)+.3;
 float m=.5*(a+e),r=sqrt(max(.000001,.25*(a-e)*(a-e)+b*b));
 float l1=max(.1,m+r),l2=max(.1,m-r);
 vec2 axis=abs(b)>.0001?normalize(vec2(b,l1-a)):(a>=e?vec2(1.,0.):vec2(0.,1.));
 vec2 delta=position.x*min(2048.,3.*sqrt(l1))*axis+position.y*min(2048.,3.*sqrt(l2))*vec2(-axis.y,axis.x);
 vec4 clip=projectionMatrix*c;
 clip.xy+=delta*2./viewport*clip.w;
 gl_Position=clip;
}`;
const fragment=`precision highp float;
varying vec2 gaussianUV;varying vec4 gaussianColor;
void main(){float r=dot(gaussianUV,gaussianUV);if(r>1.)discard;
 float alpha=gaussianColor.a*exp(-4.5*r);if(alpha<.003)discard;
 gl_FragColor=vec4(gaussianColor.rgb,alpha);}`;
export class GaussianLayer {
 constructor(scene,renderer){
  this.renderer=renderer;this.sources=[];this.dirty=true;this.busy=false;this.lastSort=0;this.lastView='';this.count=0;this.generation=0;
  const g=this.geometry=new THREE.InstancedBufferGeometry();
  g.setAttribute('position',new THREE.Float32BufferAttribute([-1,-1,0,1,-1,0,1,1,0,-1,1,0],3));g.setIndex([0,1,2,0,2,3]);g.instanceCount=0;
  this.material=new THREE.ShaderMaterial({vertexShader:vertex,fragmentShader:fragment,transparent:true,depthWrite:false,
   depthTest:true,side:THREE.DoubleSide,uniforms:{viewport:{value:new THREE.Vector2(1,1)}}});
  this.mesh=new THREE.Mesh(g,this.material);this.mesh.frustumCulled=false;this.mesh.renderOrder=10;scene.add(this.mesh);
  this.worker=new Worker(new URL('./sort-worker.js',import.meta.url),{type:'module'});
  this.worker.onerror=e=>{this.busy=false;console.error('Splat sorter failed',e);};
  this.worker.onmessage=({data})=>{this.busy=false;if(data.generation!==this.generation)return;this.upload(data.order);};
 }
 async add(url,root){const response=await fetch(url);if(!response.ok)throw Error(`Missing splat ${url}`);
  const data=parseGaussianPLY(await response.arrayBuffer());this.sources.push({data,root});this.dirty=true;return data.count;}
 rebuild(){
  this.generation++;
  const active=this.sources.filter(s=>{let o=s.root;while(o){if(!o.visible)return false;o=o.parent;}return true;});
  this.count=active.reduce((n,s)=>n+s.data.count,0);
  const centers=new Float32Array(this.count*3),scales=new Float32Array(this.count*3),quats=new Float32Array(this.count*4),colors=new Float32Array(this.count*4);
  let n=0;const v=new THREE.Vector3(),p=new THREE.Vector3(),worldQ=new THREE.Quaternion(),worldS=new THREE.Vector3(),q=new THREE.Quaternion();
  for(const {data,root} of active){root.updateWorldMatrix(true,false);root.matrixWorld.decompose(p,worldQ,worldS);
   const scale=(worldS.x+worldS.y+worldS.z)/3;
   for(let i=0;i<data.count;i++,n++){
    v.fromArray(data.centers,i*3).applyMatrix4(root.matrixWorld);v.toArray(centers,n*3);
    for(let j=0;j<3;j++)scales[n*3+j]=data.scales[i*3+j]*scale;
    q.fromArray(data.quats,i*4).premultiply(worldQ).toArray(quats,n*4);
    for(let j=0;j<4;j++)colors[n*4+j]=data.colors[i*4+j];
   }
  }
  this.arrays={centers,scales,quats,colors};this.dirty=false;this.lastView='';
  // Hide old instance data until the next matching sort returns.
  this.geometry.instanceCount=0;
 }
 upload(order){
  for(const [name,key,size] of [['splatCenter','centers',3],['splatScale','scales',3],['splatQuat','quats',4],['splatColor','colors',4]]){
   const src=this.arrays[key];let attr=this.geometry.getAttribute(name);
   if(!attr||attr.array.length!==src.length){attr=new THREE.InstancedBufferAttribute(new Float32Array(src.length),size);attr.setUsage(THREE.DynamicDrawUsage);this.geometry.setAttribute(name,attr);}
   for(let i=0;i<order.length;i++)for(let j=0;j<size;j++)attr.array[i*size+j]=src[order[i]*size+j];
   attr.needsUpdate=true;
  }
  this.geometry.instanceCount=order.length;
 }
 update(camera,time){
  if(this.dirty)this.rebuild();
  this.renderer.getDrawingBufferSize(this.material.uniforms.viewport.value);
  if(this.busy||!this.count||time-this.lastSort<150)return;
  camera.updateMatrixWorld();const m=Array.from(camera.matrixWorldInverse.elements),key=m.map(x=>x.toFixed(4)).join(',');
  if(key===this.lastView)return;
  this.lastView=key;this.lastSort=time;this.busy=true;
  const positions=this.arrays.centers.slice();this.worker.postMessage({positions,matrix:m,generation:this.generation},[positions.buffer]);
 }
}
