import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from room2sim.core import IDENTITY, inside, load_config, write_json, digest
from room2sim import splats,pipeline
from room2sim.patches import validate_patch


def tiny_ply(path):
    names=['x','y','z','f_dc_0','f_dc_1','f_dc_2','opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3','f_rest_0']
    header='ply\nformat binary_little_endian 1.0\nelement vertex 3\n'+''.join(f'property float {n}\n' for n in names)+'end_header\n'
    rows=[[-1,0,0, .1,.2,.3, 2,-3,-3,-3, 1,0,0,0,9], [0,0,0, .2,.3,.4, 2,-3,-3,-3, 1,0,0,0,8], [1,0,0,.3,.4,.5,2,-3,-3,-3,1,0,0,0,7]]
    Path(path).write_bytes(header.encode()+b''.join(struct.pack('<15f',*r) for r in rows))
    return rows


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name).resolve()
    def tearDown(self):self.tmp.cleanup()
    def test_crop_preserves_all_properties_and_source(self):
        source=self.p/'source.ply';rows=tiny_ply(source);sha=digest(source)
        out=self.p/'crop.ply';receipt=splats.crop(source,out,[{'min':[-.1,-1,-1],'max':[.1,1,1]}])
        data=splats.load(out)
        self.assertEqual(list(data['values']),[tuple(rows[0][:3])+tuple(struct.unpack('<12f',struct.pack('<12f',*rows[0][3:]))),tuple(rows[2][:3])+tuple(struct.unpack('<12f',struct.pack('<12f',*rows[2][3:])))])
        self.assertEqual(receipt['removed'],1);self.assertEqual(digest(source),sha)
    def test_reject_empty_crop_and_source_overwrite(self):
        source=self.p/'source.ply';tiny_ply(source)
        with self.assertRaises(ValueError):splats.crop(source,source,[])
        with self.assertRaises(ValueError):splats.crop(source,self.p/'empty.ply',[{'min':[-2,-2,-2],'max':[2,2,2]}])
    def test_validate_finite_gaussians(self):
        source=self.p/'source.ply';tiny_ply(source)
        raw=source.read_bytes();source.write_bytes(raw[:-4]+struct.pack('<f',float('nan')))
        with self.assertRaises(ValueError):splats.inspect(source)
    def test_package_reference_cannot_escape(self):
        with self.assertRaises(ValueError):inside(self.p,'../secret')
        self.assertEqual(inside(self.p,'assets/model.ply'),self.p/'assets/model.ply')
    def test_patch_rejects_unsafe_id_and_executable_operation(self):
        with self.assertRaises(ValueError):validate_patch({'version':1,'operations':[{'id':'../../outside','kind':'box','reason':'test'}]})
        with self.assertRaises(ValueError):validate_patch({'version':1,'operations':[{'id':'bad','kind':'python','reason':'test','code':'print(1)'}]})
    def test_config_relative_paths_and_fractional_counts(self):
        cfg=self.p/'config.json';write_json(cfg,{'version':1,'backend':'splatfacto','videos':['v.mp4'],'fps':2,'max_frames':30,'iterations':100})
        loaded=load_config(cfg);self.assertEqual(loaded['_base'],str(self.p))
        data=json.loads(cfg.read_text());data['iterations']=1.5;write_json(cfg,data)
        with self.assertRaises(ValueError):load_config(cfg)
    def test_existing_splat_repair_objects_package_without_gpu(self):
        source=self.p/'source.ply';tiny_ply(source)
        cfg=self.p/'config.json';write_json(cfg,{'version':1,'backend':'splatfacto','videos':['not-required-for-staged-import.mp4'],
          'existing_splat':'source.ply','fps':2,'max_frames':30,'iterations':100,'room_transform':IDENTITY})
        run=pipeline.new_run(cfg,self.p/'run')
        pipeline.stage_splat(run);pipeline.stage_repair(run);pipeline.stage_objects(run)
        if not (ROOT/'web/dist/index.html').exists():self.skipTest('Needs prebuilt viewer')
        out=pipeline.stage_package(run,self.p/'site');result=pipeline.validate_package(out)
        self.assertEqual(result['assets'],1);self.assertEqual(digest(out/'assets/room.ply'),digest(source))
        manifest=json.loads((out/'scene.json').read_text());self.assertEqual(manifest['objects'],[])
        (out/'assets/room.ply').write_bytes(b'changed')
        with self.assertRaises(ValueError):pipeline.validate_package(out)
    def test_stage_receipt_detects_tampering(self):
        cfg=self.p/'config.json';write_json(cfg,{'version':1,'backend':'splatfacto','videos':['a.mp4'],'fps':1,'max_frames':10,'iterations':100})
        run=pipeline.new_run(cfg,self.p/'run');file=run/'frame.jpg';file.write_bytes(b'one')
        pipeline.finish(run,'ingest',[file]);file.write_bytes(b'two')
        with self.assertRaises(RuntimeError):pipeline.verify_stage(run,'ingest')
    def test_review_is_a_separate_module_with_stale_scene_guard(self):
        spec=importlib.util.spec_from_file_location('review',ROOT/'agents/review.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.assertEqual(module.SCHEMA['properties']['patch']['properties']['version']['enum'],[1])
        source=self.p/'source.ply';tiny_ply(source)
        pkg=self.p/'package';pkg.mkdir();shutil.copy2(source,pkg/'room.ply')
        write_json(pkg/'scene.json',{'version':1,'room':{'representation':'splat','asset':'room.ply','transform':IDENTITY},'objects':[]})
        write_json(pkg/'checksums.json',{'scene.json':digest(pkg/'scene.json'),'room.ply':digest(pkg/'room.ply')})
        review=self.p/'review.json';write_json(review,{'scene_sha256':'wrong','verdict':'repair','patch':{'version':1,'operations':[]}})
        with self.assertRaisesRegex(ValueError,'stale'):module.apply(pkg,review,self.p/'candidate')
        self.assertFalse((self.p/'candidate').exists())


if __name__=='__main__':unittest.main()
