import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));
const dist=path.join(here,'dist');
fs.mkdirSync(dist,{recursive:true});
for(const file of ['index.html','app.js','gaussians.js','ply.js','sort-worker.js','interaction.js','node-objects.js','style.css'])
  fs.copyFileSync(path.join(here,file),path.join(dist,file));
// A pre-installed Three.js is sufficient. No network or package manager invocation.
const threeRoot=process.env.THREE_MODULE_ROOT || path.join(here,'node_modules/three');
if(!fs.existsSync(path.join(threeRoot,'build/three.module.js')))
  throw Error('Three.js 0.170.0 must already be installed; set THREE_MODULE_ROOT or provide web/node_modules/three.');
fs.mkdirSync(path.join(dist,'vendor'),{recursive:true});
fs.copyFileSync(path.join(threeRoot,'build/three.module.js'),path.join(dist,'vendor/three.module.js'));
fs.copyFileSync(path.join(threeRoot,'LICENSE'),path.join(dist,'vendor/THREE-LICENSE.txt'));
// Bundle only the addon modules this viewer imports, including transitive dependencies.
const addons=path.join(dist,'vendor/addons');
fs.rmSync(addons,{recursive:true,force:true});
for(const relative of ['controls/OrbitControls.js','loaders/GLTFLoader.js','utils/BufferGeometryUtils.js']){
 const destination=path.join(addons,relative);fs.mkdirSync(path.dirname(destination),{recursive:true});
 fs.copyFileSync(path.join(threeRoot,'examples/jsm',relative),destination);
}
console.log(`Offline viewer built at ${dist}`);
