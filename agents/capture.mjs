/* Use an already installed Playwright, including playwright-core with Chrome.
   Starts an ephemeral localhost server, records screenshots and interaction evidence. */
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const [pkgArg,outArg]=process.argv.slice(2);
if(!pkgArg||!outArg)throw Error('Usage: node agents/capture.mjs PACKAGE EVIDENCE_DIRECTORY');
const pkg=path.resolve(pkgArg),out=path.resolve(outArg);
if(fs.existsSync(out))throw Error('Evidence destination exists; use a fresh directory');
const playwright=require(process.env.PLAYWRIGHT_MODULE || 'playwright');
fs.mkdirSync(out,{recursive:true});
const types={'.html':'text/html','.js':'application/javascript','.css':'text/css','.json':'application/json','.glb':'model/gltf-binary','.ply':'application/octet-stream','.jpg':'image/jpeg','.png':'image/png'};
const server=http.createServer((req,res)=>{
 const decoded=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
 const file=path.resolve(pkg,'.'+(decoded==='/'?'/index.html':decoded));
 if(!file.startsWith(pkg+path.sep)||!fs.existsSync(file)||!fs.statSync(file).isFile()){res.writeHead(404);res.end();return;}
 res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');fs.createReadStream(file).pipe(res);
});
const routeFiles=process.env.ROOM2SIM_FILE_ROUTES==='1';
if(!routeFiles)await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
const hashFile=name=>createHash('sha256').update(fs.readFileSync(path.join(pkg,name))).digest('hex');
const evidenceBinding={scene_sha256:hashFile('scene.json'),package_sha256:hashFile('checksums.json')};
let browser;
try{
 browser=await playwright.chromium.launch({headless:true,...(process.env.BROWSER_BIN?{executablePath:process.env.BROWSER_BIN}:{})});
 const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 if(routeFiles)await page.context().route('https://room2sim.local/**',async route=>{
  const name=decodeURIComponent(new URL(route.request().url()).pathname);
  const file=path.resolve(pkg,'.'+(name==='/'?'/index.html':name));
  if(!file.startsWith(pkg+path.sep)||!fs.existsSync(file))return route.fulfill({status:404,body:''});
  await route.fulfill({status:200,contentType:types[path.extname(file)]||'application/octet-stream',body:fs.readFileSync(file)});
 });
 await page.goto(routeFiles?'https://room2sim.local/':`http://127.0.0.1:${server.address().port}`,{waitUntil:'load'});
 await page.waitForFunction(()=>window.room2sim?.state.ready,undefined,{timeout:120000});
 // Wait for asynchronous sorter and GPU to produce the first frame, then settle.
 await page.waitForFunction(()=>document.querySelector('#status')?.textContent.startsWith('Ready'));
 await page.waitForTimeout(2000);
 const manifest=JSON.parse(fs.readFileSync(path.join(pkg,'scene.json'),'utf8'));
 let views=manifest.review_views;
 if(!views&&manifest.camera_views){const poses=JSON.parse(fs.readFileSync(path.join(pkg,manifest.camera_views),'utf8'));views=[poses[0],poses[Math.floor(poses.length/2)],poses[poses.length-1]];}
 views=views||[manifest.camera];
 const screenshots=[];
 for(let i=0;i<Math.min(4,views.length);i++){
  await page.evaluate(view=>window.room2sim.setCamera(view),views[i]);await page.waitForTimeout(1200);
  const filename=`view-${i}.png`;await page.screenshot({path:path.join(out,filename)});screenshots.push({file:filename,camera:views[i],scope:'full hybrid viewer'});
 }
 const before=await page.evaluate(()=>window.room2sim.snapshot());
 let movement=null;
 if(before.length){
  await page.locator('#objects').selectOption(before[0].id);
  movement=await page.evaluate(id=>window.room2sim.move(id,[0,.15,0]),before[0].id);
  await page.waitForTimeout(1200);await page.screenshot({path:path.join(out,'object-moved.png')});
  const after=await page.evaluate(()=>window.room2sim.snapshot());
  await page.locator('#reset').click();await page.waitForTimeout(300);
  const reset=await page.evaluate(()=>window.room2sim.snapshot());
  movement={accepted:movement,before,after,reset,reset_matches:JSON.stringify(before)===JSON.stringify(reset)};
 }
 if(evidenceBinding.scene_sha256!==hashFile('scene.json')||evidenceBinding.package_sha256!==hashFile('checksums.json'))throw Error('Package changed during capture; capture again');
 const ready=await page.evaluate(()=>({ready:window.room2sim.state.ready,errors:window.room2sim.state.errors}));
 fs.writeFileSync(path.join(out,'browser.json'),JSON.stringify({version:1,...evidenceBinding,...ready,page_errors:errors,screenshots,movement,renderer:'perspective Gaussian covariance; SH0; no physical dynamics'},null,2));
 if(errors.length||ready.errors.length||!ready.ready||movement?.reset_matches===false)throw Error('Browser check failed; inspect browser.json');
 console.log(`Browser evidence: ${out}`);
}finally{if(browser)await browser.close();if(server.listening)await new Promise(resolve=>server.close(resolve));}
