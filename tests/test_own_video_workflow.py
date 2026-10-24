"""Offline guide contracts: no model, GPU, Blender, network, or paid API call."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools')]
from room2sim.core import IDENTITY,digest,write_json,load_config,resolve
from room2sim import pipeline
from config_from_package import create
from align_package import align
from project_metadata import metadata
from render_guides import build_guides
from test_pipeline import tiny_ply
from room2sim.patches import validate_patch, repair_objects
from room2sim.core import transform
spec=importlib.util.spec_from_file_location('guide_review',ROOT/'agents/review.py');review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)


class OwnVideoWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name).resolve();self.pkg=self.p/'package';self.pkg.mkdir()
        self.video=self.p/'video.mp4';self.video.write_bytes(b'fixture; never decoded')
        tiny_ply(self.pkg/'room.ply');raw=bytearray((self.pkg/'room.ply').read_bytes());offset=raw.index(b'end_header\n')+len(b'end_header\n')
        struct.pack_into('<3f',raw,offset+60,0,1,0);struct.pack_into('<3f',raw,offset+120,1,0,1)
        (self.pkg/'bottle.ply').write_bytes(raw);(self.pkg/'viewer.js').write_text('// custom reviewed viewer must survive alignment\n')
        self.manifest={'version':1,'title':'Fixture room','room':{'representation':'splat','asset':'room.ply','transform':IDENTITY},
          'camera':{'position':[3,2,3],'target':[0,0,0]},'objects':[{'id':'bottle','representation':'splat','asset':'bottle.ply','transform':IDENTITY,
          'collider':{'type':'box','center':[0,0,0],'dimensions':[1,1,1]}}],'world':{'units':'uncalibrated'},'provenance':{}}
        write_json(self.pkg/'scene.json',self.manifest);self.hashes()
    def tearDown(self):self.tmp.cleanup()
    def hashes(self):write_json(self.pkg/'checksums.json',{p.name:digest(p) for p in self.pkg.iterdir() if p.name!='checksums.json'})
    def placements(self,data=None):
        path=self.p/'placements.json';write_json(path,data or {'version':1,'objects':[{'id':'bottle','transform':{'position':[1,2,3],'quaternion':[0,0,0,1],'scale':.3}}]});return path
    def test_review_crop_import_and_package_sequence_runs_offline(self):
        result=self.p/'review.json';write_json(result,{'scene_sha256':digest(self.pkg/'scene.json'),'package_sha256':digest(self.pkg/'checksums.json'),
          'verdict':'repair','patch':{'version':1,'operations':[{'id':'crop','reason':'fixture','kind':'crop_splats','min':[-.1,-.1,-.1],'max':[.1,.1,.1]}]}})
        candidate=self.p/'candidate';review.apply(self.pkg,result,candidate)
        cfg=self.p/'configs/reuse.json';create(candidate,self.video,cfg)
        loaded=load_config(cfg);self.assertEqual(resolve(loaded['_base'],loaded['existing_splat']),candidate/'evidence/astra-candidate/room.ply')
        self.assertEqual(loaded['room_transform'],IDENTITY)
        run=pipeline.new_run(cfg,self.p/'run');pipeline.stage_splat(run);pipeline.stage_repair(run);pipeline.stage_objects(run)
        output=pipeline.stage_package(run,self.p/'out');self.assertEqual(pipeline.validate_package(output)['assets'],2)
        self.assertEqual(json.loads((output/'scene.json').read_text())['objects'][0]['id'],'bottle')
    def test_package_config_rejects_mesh_demo_and_existing_destination(self):
        cfg=self.p/'cfg.json';create(self.pkg,self.video,cfg)
        with self.assertRaisesRegex(ValueError,'destination exists'):create(self.pkg,self.video,cfg)
        self.manifest['room']['representation']='mesh';write_json(self.pkg/'scene.json',self.manifest);self.hashes()
        with self.assertRaises(ValueError):create(self.pkg,self.video,self.p/'other.json')
    def test_alignment_fits_proxy_and_preserves_assets_viewer_and_source(self):
        old=digest(self.pkg/'checksums.json');out=self.p/'aligned';align(self.pkg,self.placements(),out,True)
        obj=json.loads((out/'scene.json').read_text())['objects'][0]
        self.assertEqual(obj['transform']['position'],[1,2,3]);self.assertEqual(obj['collider']['dimensions'],[2,1,1])
        self.assertEqual(obj['collider']['center'],[0,.5,.5]);self.assertEqual(digest(out/'bottle.ply'),digest(self.pkg/'bottle.ply'))
        self.assertEqual((out/'viewer.js').read_bytes(),(self.pkg/'viewer.js').read_bytes());self.assertEqual(digest(self.pkg/'checksums.json'),old)
        pipeline.validate_package(out)
    def test_alignment_rejects_unknown_ids_invalid_scale_and_source_overwrite(self):
        edits={'version':1,'objects':[{'id':'unknown','transform':IDENTITY}]}
        with self.assertRaisesRegex(ValueError,'Unknown'):align(self.pkg,self.placements(edits),self.p/'unknown')
        edits['objects'][0]={'id':'bottle','transform':{**IDENTITY,'scale':-1}}
        with self.assertRaises(ValueError):align(self.pkg,self.placements(edits),self.p/'invalid')
        with self.assertRaises(ValueError):align(self.pkg,self.placements(),self.pkg/'nested')
        self.assertFalse((self.p/'invalid').exists())
    def test_explicit_collider_overrides_approximate_fit(self):
        data={'version':1,'objects':[{'id':'bottle','transform':IDENTITY,'collider':{'type':'box','center':[0,0,0],'dimensions':[.2,.3,.4]}}]}
        out=self.p/'custom';align(self.pkg,self.placements(data),out,True)
        self.assertEqual(json.loads((out/'scene.json').read_text())['objects'][0]['collider']['dimensions'],[.2,.3,.4])
    def test_destination_repository_and_ref_are_injected_without_personal_owner(self):
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'destination/room-example','GITHUB_REF_NAME':'feature/guide'},clear=True):
            result=metadata()
        self.assertEqual(result['repository_url'],'https://github.com/destination/room-example')
        self.assertIn('/blob/feature%2Fguide/',result['source_url'])
        with self.assertRaises(ValueError):metadata('https://wrong.example/owner/repo','main')
    def test_static_guides_are_generated_from_markdown_with_code_and_sources(self):
        build_guides(self.p)
        html=(self.p/'guide.html').read_text();self.assertIn('tools/align_package.py',html);self.assertIn('future.html',html)
        self.assertIn('OPENAI_API_KEY',html);self.assertIn('32 GB',html)
        self.assertIn('https://arxiv.org/abs/2403.06738',(self.p/'future.html').read_text())


    def shape(self,interactive=True):
        return {'id':'replacement','kind':'box','position':[1,2,3],
          'dimensions':[.2,.4,.3],'rotation':[.1,.2,.3],'color':[.5,.5,.5],
          'reason':'offline fixture','interactive':interactive}
    def review_file(self,operations):
        result=self.p/'review.json';write_json(result,{'scene_sha256':digest(self.pkg/'scene.json'),
          'package_sha256':digest(self.pkg/'checksums.json'),'verdict':'repair',
          'patch':{'version':1,'operations':operations}});return result
    def exported_box(self,path,name='replacement'):
        # Local Blender-output contract fixture; no Blender or API invocation.
        vertices=struct.pack('<9f',0,0,0,1,0,0,0,1,0)
        doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
          'nodes':[{'name':name,'children':[1]},{'name':name+'_mesh','mesh':0}],
          'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],
          'buffers':[{'byteLength':len(vertices)}], 'bufferViews':[{'buffer':0,'byteLength':len(vertices)}],
          'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[0,0,0],'max':[1,1,0]}]}
        raw=json.dumps(doc).encode();raw+=b' '*((-len(raw))%4)
        path.write_bytes(struct.pack('<4sII',b'glTF',2,28+len(raw)+len(vertices))+struct.pack('<I4s',len(raw),b'JSON')+raw+struct.pack('<I4s',len(vertices),b'BIN\x00')+vertices)
    def test_movable_repair_contract_is_explicit_and_legacy_shapes_stay_static(self):
        op=self.shape();objects=repair_objects({'version':1,'operations':[op]})
        self.assertEqual(objects[0]['node_source'],'repairs');transform(objects[0]['transform'])
        self.assertEqual(objects[0]['collider']['dimensions'],op['dimensions'])
        for value in [False,None]:
            old=self.shape(False)
            if value is None:old.pop('interactive')
            self.assertEqual(repair_objects({'version':1,'operations':[old]}),[])
        bad=self.shape();bad['interactive']='true'
        with self.assertRaises(ValueError):validate_patch({'version':1,'operations':[bad]})
    def test_api_schema_requires_explicit_interaction_choice_for_shapes(self):
        for variant in review.PATCH_SCHEMA['properties']['operations']['items']['anyOf']:
            kind=variant['properties']['kind']['enum'][0]
            if kind in ('box','table','cylinder'):
                self.assertIn('interactive',variant['required'])
                self.assertEqual(variant['properties']['interactive'],{'type':'boolean'})
    def test_apply_registers_repaired_object_and_preserves_source_and_existing_objects(self):
        old=digest(self.pkg/'checksums.json');result=self.review_file([self.shape()]);out=self.p/'refined'
        def export(cmd,log):
            self.assertIn('--python',cmd);dest=Path(cmd[cmd.index('--output')+1]);self.exported_box(dest/'repairs.glb')
        with patch.object(review,'executable',return_value='blender'),patch.object(review,'run_command',side_effect=export):
            review.apply(self.pkg,result,out)
        data=json.loads((out/'scene.json').read_text())
        self.assertEqual([obj['id'] for obj in data['objects']],['bottle','replacement'])
        self.assertEqual(data['objects'][1]['node_source'],'repairs')
        self.assertEqual(digest(self.pkg/'checksums.json'),old);pipeline.validate_package(out)
    def test_duplicate_repair_object_is_rejected_before_output_or_blender(self):
        op=self.shape();op['id']='bottle';result=self.review_file([op]);out=self.p/'duplicate'
        with self.assertRaisesRegex(ValueError,'already exists'):review.apply(self.pkg,result,out)
        self.assertFalse(out.exists())
    def test_missing_exported_repair_node_cannot_finalize_candidate(self):
        result=self.review_file([self.shape()]);out=self.p/'bad-export'
        def export(cmd,log):self.exported_box(Path(cmd[cmd.index('--output')+1])/'repairs.glb','wrong')
        with patch.object(review,'executable',return_value='blender'),patch.object(review,'run_command',side_effect=export):
            with self.assertRaisesRegex(RuntimeError,'interactive repair node'):review.apply(self.pkg,result,out)
        self.assertNotIn('mesh',json.loads((out/'scene.json').read_text())['room'])


if __name__=='__main__':unittest.main()
