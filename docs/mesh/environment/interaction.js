// Pure functions shared by browser and executable tests.
export function aabb(center,dimensions){return {min:center.map((c,i)=>c-dimensions[i]/2),max:center.map((c,i)=>c+dimensions[i]/2)};}
export function intersects(a,b){return a.min.every((v,i)=>v<b.max[i]&&a.max[i]>b.min[i]);}
export function permittedMove(center,dimensions,obstacles){return !obstacles.some(o=>intersects(aabb(center,dimensions),o));}
export function finiteTransform(t){return t.position.length===3&&t.quaternion.length===4&&[...t.position,...t.quaternion,t.scale].every(Number.isFinite)&&t.scale>0;}
