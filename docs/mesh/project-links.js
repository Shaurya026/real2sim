// The build writes destination metadata from GITHUB_REPOSITORY / source ref.
// Relative scene links remain unchanged on forks, custom domains and project paths.
export function projectLink(metadata,path){
 if(!metadata?.repository_url)return null;
 if(path==='repository')return metadata.repository_url;
 if(!metadata.source_url||path.split('/').some(part=>part==='..')||path.startsWith('/'))return null;
 return metadata.source_url+path.split('/').map(encodeURIComponent).join('/');
}
if(typeof document!=='undefined'){
 try{const response=await fetch(new URL('./project.json',import.meta.url));if(!response.ok)throw Error('No project metadata');const metadata=await response.json();
  for(const link of document.querySelectorAll('[data-project-link]')){const target=projectLink(metadata,link.dataset.projectLink);if(target)link.href=target;else if(link.dataset.projectLink==='repository')link.textContent='Project guide ↗';}
 }catch{for(const link of document.querySelectorAll('[data-project-link="repository"]')){link.href='guide.html';link.textContent='Project guide ↗';}}
}
