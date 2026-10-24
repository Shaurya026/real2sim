"""Regression coverage for run, package and visual-review evidence integrity."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from room2sim import pipeline
from room2sim.core import digest,write_json
from test_pipeline import tiny_ply

spec=importlib.util.spec_from_file_location('review_integrity',ROOT/'agents/review.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def package(self):
        pkg=self.p/'package';pkg.mkdir();tiny_ply(pkg/'room.ply')
        write_json(pkg/'scene.json',{'version':1,'room':{'representation':'splat','asset':'room.ply'},'objects':[]})
        write_json(pkg/'checksums.json',{name:digest(pkg/name) for name in ('scene.json','room.ply')})
        return pkg
    def test_modified_frozen_run_config_is_rejected(self):
        cfg=self.p/'config.json'
        write_json(cfg,{'version':1,'backend':'splatfacto','videos':['video.mp4'],'fps':1,'max_frames':10,'iterations':100})
        run=pipeline.new_run(cfg,self.p/'run')
        self.assertEqual(pipeline.run_config(run)['iterations'],100)
        data=json.loads((run/'config.json').read_text());data['iterations']=1000
        write_json(run/'config.json',data)
        with self.assertRaisesRegex(RuntimeError,'Run config changed'):
            pipeline.run_config(run)
    def test_package_cannot_omit_asset_hashes(self):
        pkg=self.package();pipeline.validate_package(pkg)
        write_json(pkg/'checksums.json',{'scene.json':digest(pkg/'scene.json')})
        with self.assertRaisesRegex(ValueError,'Missing checksums.*room.ply'):
            pipeline.validate_package(pkg)
    def test_package_cannot_omit_viewer_hashes(self):
        pkg=self.package();(pkg/'app.js').write_text('console.log("changed viewer")')
        with self.assertRaisesRegex(ValueError,'Missing checksums.*app.js'):
            pipeline.validate_package(pkg)
    def test_same_manifest_with_changed_asset_invalidates_review(self):
        pkg=self.package();manifest_hash=digest(pkg/'scene.json');old_hash=digest(pkg/'checksums.json')
        source=pkg/'room.ply';source.write_bytes(source.read_bytes().replace(b'element vertex 3',b'comment changed\nelement vertex 3'))
        write_json(pkg/'checksums.json',{name:digest(pkg/name) for name in ('scene.json','room.ply')})
        pipeline.validate_package(pkg)
        result=self.p/'review.json';write_json(result,{'scene_sha256':manifest_hash,'package_sha256':old_hash,
            'verdict':'repair','patch':{'version':1,'operations':[]}})
        with self.assertRaisesRegex(ValueError,'package assets or viewer differ'):
            review.apply(pkg,result,self.p/'candidate')
        self.assertFalse((self.p/'candidate').exists())
    def test_prepare_rejects_screenshots_from_different_package(self):
        pkg=self.package();evidence=self.p/'evidence';evidence.mkdir()
        write_json(evidence/'browser.json',{'ready':True,'scene_sha256':digest(pkg/'scene.json'),
            'package_sha256':'old','screenshots':[]})
        with self.assertRaisesRegex(ValueError,'Browser evidence is stale'):
            review.prepare(pkg,evidence,self.p/'request',[])
    def test_prepare_carries_exact_package_binding(self):
        pkg=self.package();evidence=self.p/'evidence';evidence.mkdir()
        write_json(evidence/'browser.json',{'ready':True,'scene_sha256':digest(pkg/'scene.json'),
            'package_sha256':digest(pkg/'checksums.json'),'screenshots':[]})
        review.prepare(pkg,evidence,self.p/'request',[])
        data=json.loads((self.p/'request/request.json').read_text())
        self.assertEqual(data['package_sha256'],digest(pkg/'checksums.json'))


if __name__=='__main__':
    unittest.main()
