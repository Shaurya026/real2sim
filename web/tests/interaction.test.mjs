import test from 'node:test';
import assert from 'node:assert/strict';
import {aabb,intersects,permittedMove,finiteTransform} from '../interaction.js';
test('touching is permitted but overlapping an obstacle is blocked',()=>{
 const obstacle=aabb([0,0,0],[2,2,2]);
 assert.equal(permittedMove([2,0,0],[2,2,2],[obstacle]),true);
 assert.equal(permittedMove([1.9,0,0],[2,2,2],[obstacle]),false);
 assert.equal(intersects(obstacle,aabb([0,4,0],[1,1,1])),false);
});
test('invalid placement numbers cannot be exported as finite transforms',()=>{
 assert.equal(finiteTransform({position:[0,0,0],quaternion:[0,0,0,1],scale:1}),true);
 assert.equal(finiteTransform({position:[NaN,0,0],quaternion:[0,0,0,1],scale:1}),false);
});
