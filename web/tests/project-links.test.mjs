import test from 'node:test';
import assert from 'node:assert/strict';
import {projectLink} from '../../docs/mesh/project-links.js';
test('source links follow the destination repository and source ref',()=>{
 const metadata={repository_url:'https://github.com/destination/example',source_url:'https://github.com/destination/example/blob/feature%2Fguide/'};
 assert.equal(projectLink(metadata,'repository'),metadata.repository_url);
 assert.equal(projectLink(metadata,'docs/OWN_VIDEO.md'),metadata.source_url+'docs/OWN_VIDEO.md');
});
test('local source has no personal fork fallback and unsafe paths are rejected',()=>{
 assert.equal(projectLink({repository_url:null},'repository'),null);
 const meta={repository_url:'https://github.com/team/repo',source_url:'https://github.com/team/repo/blob/HEAD/'};
 assert.equal(projectLink(meta,'../secret'),null);assert.equal(projectLink(meta,'/absolute'),null);
});
