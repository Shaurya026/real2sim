const types={float:['getFloat32',4],float32:['getFloat32',4],double:['getFloat64',8],float64:['getFloat64',8],
 uchar:['getUint8',1],uint8:['getUint8',1],char:['getInt8',1],int8:['getInt8',1],int:['getInt32',4],int32:['getInt32',4],
 uint:['getUint32',4],uint32:['getUint32',4],short:['getInt16',2],int16:['getInt16',2],ushort:['getUint16',2],uint16:['getUint16',2]};
export function parseGaussianPLY(buffer){
 const bytes=new Uint8Array(buffer), decoder=new TextDecoder();
 let end=-1;
 for(let i=0;i<Math.min(bytes.length,65536)-10;i++){
  if(bytes[i]===101 && decoder.decode(bytes.subarray(i,i+10))==='end_header'){
   end=i+10;if(bytes[end]===13)end++;if(bytes[end]!==10)throw Error('Invalid PLY header delimiter');end++;break;
  }
 }
 if(end<0)throw Error('Missing Gaussian PLY header');
 const header=decoder.decode(bytes.subarray(0,end)); let format,count,offset=0,element; const props={};
 for(const line of header.split(/\r?\n/)){
  const t=line.trim().split(/\s+/);
  if(t[0]==='format')format=t[1];
  if(t[0]==='element'){element=t[1];if(element!=='vertex')throw Error('Expected Gaussian vertex-only PLY');count=Number(t[2]);}
  if(t[0]==='property'&&element==='vertex'){
   if(!types[t[1]])throw Error('Unsupported Gaussian property type');
   if(props[t[2]])throw Error('Duplicate Gaussian property');
   props[t[2]]={offset,index:Object.keys(props).length,type:types[t[1]]};offset+=types[t[1]][1];
  }
 }
 for(const key of ['x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3'])
  if(!props[key])throw Error(`Not Gaussian PLY: ${key} missing`);
 if(!Number.isInteger(count)||count<=0||count>4000000)throw Error('Gaussian count must be 1–4,000,000 for this review viewer');
 const view=new DataView(buffer), little=format==='binary_little_endian';
 let rows;
 if(format==='ascii')rows=decoder.decode(bytes.subarray(end)).trim().split(/\r?\n/).map(r=>r.trim().split(/\s+/).map(Number));
 else if(!['binary_little_endian','binary_big_endian'].includes(format)||end+count*offset!==bytes.length)throw Error('Invalid binary PLY length/format');
 if(rows&&(rows.length!==count||rows.some(r=>r.length!==Object.keys(props).length||r.some(x=>!Number.isFinite(x)))))throw Error('Invalid ASCII PLY rows');
 function read(i,k){const p=props[k];return rows?rows[i][p.index]:view[p.type[0]](end+i*offset+p.offset,little);}
 const centers=new Float32Array(count*3),scales=new Float32Array(count*3),quats=new Float32Array(count*4),colors=new Float32Array(count*4);
 for(let i=0;i<count;i++){
  for(let j=0;j<3;j++){
   centers[i*3+j]=read(i,['x','y','z'][j]);
   scales[i*3+j]=Math.exp(Math.max(-20,Math.min(10,read(i,`scale_${j}`))));
   colors[i*4+j]=Math.max(0,Math.min(1,.5+.28209479177387814*read(i,`f_dc_${j}`)));
  }
  const q=[read(i,'rot_1'),read(i,'rot_2'),read(i,'rot_3'),read(i,'rot_0')]; const norm=Math.hypot(...q)||1;
  for(let j=0;j<4;j++)quats[i*4+j]=q[j]/norm;
  colors[i*4+3]=1/(1+Math.exp(-read(i,'opacity')));
 }
 if([centers,scales,quats,colors].some(a=>a.some(x=>!Number.isFinite(x))))throw Error('Nonfinite Gaussian attributes');
 return {count,centers,scales,quats,colors};
}
