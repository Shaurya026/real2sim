import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from room2sim.core import digest,write_json
from room2sim.uploads import pointer,restore_assets,check_checkout
from room2sim.pipeline import validate_package
from test_pipeline import tiny_ply

class UploadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.p=Path(self.tmp.name).resolve()
        self.source=self.p/'source.ply';tiny_ply(self.source)
        self.repo=self.p/'repo';self.repo.mkdir()
        self.name='demo/desk/assets/room.ply'
        write_json(self.repo/'assets-manifest.json',{'version':1,'assets':[
          {'path':self.name,'bytes':self.source.stat().st_size,'sha256':digest(self.source),'required':True}]})
        self.archive=self.p/'assets.zip'
        with zipfile.ZipFile(self.archive,'w') as z:z.write(self.source,self.name)
    def tearDown(self):self.tmp.cleanup()
    def test_restores_missing_asset_and_existing_lfs_pointer(self):
        dest=self.repo/self.name;dest.parent.mkdir(parents=True)
        dest.write_text('version https://git-lfs.github.com/spec/v1\noid sha256:123\nsize 12\n')
        self.assertTrue(pointer(dest))
        result=restore_assets(self.archive,self.repo)
        self.assertEqual(result['restored'],[self.name]);self.assertEqual(digest(dest),digest(self.source))
        self.assertEqual(restore_assets(self.archive,self.repo)['restored'],[])
    def test_modified_asset_is_preserved(self):
        dest=self.repo/self.name;dest.parent.mkdir(parents=True);dest.write_bytes(b'local edits')
        with self.assertRaisesRegex(ValueError,'Existing asset differs'):restore_assets(self.archive,self.repo)
        self.assertEqual(dest.read_bytes(),b'local edits')
    def test_unexpected_archive_path_never_writes_checkout(self):
        with zipfile.ZipFile(self.archive,'w') as z:z.writestr('../outside',b'bad')
        with self.assertRaisesRegex(ValueError,'Unexpected archive entry'):restore_assets(self.archive,self.repo)
        self.assertFalse((self.repo/self.name).exists())
    def test_package_lfs_error_is_actionable(self):
        dest=self.repo/'model.glb';dest.write_text('version https://git-lfs.github.com/spec/v1\n')
        write_json(self.repo/'scene.json',{'version':1,'room':{'asset':'model.glb','representation':'mesh'},'objects':[]})
        with self.assertRaisesRegex(ValueError,'Git LFS pointer'):validate_package(self.repo)
    def test_checkout_reports_missing_assets_instead_of_crashing(self):
        result=check_checkout(self.repo)
        self.assertEqual(result['status'],'incomplete');self.assertEqual(result['assets'][0]['status'],'missing')
        self.assertIn('room2sim.py',result['missing_code'])

if __name__=='__main__':unittest.main()
