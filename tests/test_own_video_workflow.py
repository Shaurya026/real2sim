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
        output=pipeline.stage_package(run,self.p/'out');self.assertEqual(pipeline.validate_package(output)['assets'],1)
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


if __name__=='__main__':unittest.main()
