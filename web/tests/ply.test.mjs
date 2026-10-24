import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseGaussianPLY} from '../ply.js';
const names=['x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3'];
test('binary Gaussian parser retains a first payload byte that happens to be newline',()=>{
 const header=Buffer.from('ply\nformat binary_little_endian 1.0\nelement vertex 1\n'+names.map(n=>`property float ${n}\n`).join('')+'end_header\n');
 const body=Buffer.alloc(names.length*4);body.writeUInt32LE(10,0);body.writeFloatLE(1,40);
 const file=Buffer.concat([header,body]);const parsed=parseGaussianPLY(file.buffer.slice(file.byteOffset,file.byteOffset+file.byteLength));
 assert.equal(parsed.count,1);assert.equal(parsed.centers[0],new Float32Array(new Uint32Array([10]).buffer)[0]);
 assert.equal(parsed.colors[3],.5);assert.equal(parsed.quats[3],1);
});
const deskFile=new URL('../../demo/desk/assets/room.ply',import.meta.url);
let deskPresent=fs.existsSync(deskFile);
if(deskPresent){const fd=fs.openSync(deskFile,'r'),head=Buffer.alloc(3);fs.readSync(fd,head,0,3,0);fs.closeSync(fd);deskPresent=head.toString()==='ply';}
test('supplied desk splat decodes as 228,043 anisotropic Gaussians',{skip:!deskPresent},()=>{
 const file=fs.readFileSync(new URL('../../demo/desk/assets/room.ply',import.meta.url));
 const parsed=parseGaussianPLY(file.buffer.slice(file.byteOffset,file.byteOffset+file.byteLength));
 assert.equal(parsed.count,228043);assert.equal(parsed.scales.length,228043*3);
 assert.ok(parsed.colors.every(x=>x>=0&&x<=1));assert.ok(parsed.scales.every(x=>x>0));
});
test('reject point clouds without Gaussian attributes',()=>{
 const raw=new TextEncoder().encode('ply\nformat ascii 1.0\nelement vertex 1\nproperty float x\nproperty float y\nproperty float z\nend_header\n0 0 0\n');
 assert.throws(()=>parseGaussianPLY(raw.buffer),/Not Gaussian PLY/);
});
test('malformed ASCII row counts produce a useful validation error',()=>{
 const header='ply\nformat ascii 1.0\nelement vertex 2\n'+names.map(n=>`property float ${n}\n`).join('')+'end_header\n';
 const row=names.map(()=>0).join(' ');
 assert.throws(()=>parseGaussianPLY(new TextEncoder().encode(header+row+'\n').buffer),/Invalid ASCII PLY rows/);
 assert.throws(()=>parseGaussianPLY(new TextEncoder().encode(header+'0 0 0\n0 0 0\n').buffer),/Invalid ASCII PLY rows/);
});
test('duplicate Gaussian attributes are rejected',()=>{
 const header='ply\nformat ascii 1.0\nelement vertex 1\n'+names.map(n=>`property float ${n}\n`).join('')+'property float x\nend_header\n';
 assert.throws(()=>parseGaussianPLY(new TextEncoder().encode(header).buffer),/Duplicate Gaussian property/);
});
