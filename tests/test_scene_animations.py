"""Regression checks against original scene tracks, including corrupt buffers."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from check_scene_animations import check_animations


class SceneAnimationTests(unittest.TestCase):
    def source(self):
        return ROOT/'docs/mesh/booth/room.glb'
    def track_offset(self,raw):
        length=struct.unpack_from('<I',raw,12)[0]
        doc=json.loads(raw[20:20+length]);sampler=doc['animations'][0]['samplers'][0]
        a=doc['accessors'][sampler['input']];view=doc['bufferViews'][a['bufferView']]
        return 20+length+8+view.get('byteOffset',0)+a.get('byteOffset',0),view.get('byteStride',4)
    def test_yellow_room_contains_original_nine_second_motion(self):
        clips=check_animations(self.source())
        self.assertEqual(clips[0]['seconds'],9)
        self.assertEqual(clips[0]['channels'],13)
    def test_pantry_contains_original_fourteen_second_pickup(self):
        clips=check_animations(ROOT/'docs/mesh/pantry/room.glb')
        self.assertEqual(clips[0]['seconds'],14)
        self.assertIn('Snack packet',clips[0]['name'])
    def test_nonfinite_animation_time_is_rejected(self):
        raw=bytearray(self.source().read_bytes());offset,_=self.track_offset(raw)
        struct.pack_into('<f',raw,offset,float('nan'))
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'invalid.glb';path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'Nonfinite animation'):
                check_animations(path)
    def test_duplicate_animation_time_is_rejected(self):
        raw=bytearray(self.source().read_bytes());offset,stride=self.track_offset(raw)
        raw[offset+stride:offset+stride+4]=raw[offset:offset+4]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'invalid.glb';path.write_bytes(raw)
            with self.assertRaisesRegex(ValueError,'times must increase'):
                check_animations(path)


if __name__=='__main__':unittest.main()
