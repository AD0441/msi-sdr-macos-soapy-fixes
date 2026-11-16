"""Offline recovery guardrails; no Mac, credentials, app launches or USB required."""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recovery', ROOT / 'scripts/msi_recovery.py')
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_damaged_asset_is_rejected(self):
        file = self.root / 'input.zip'
        file.write_bytes(b'original')
        lock = {'assets': {'input': {'filename': file.name, 'sha256': recovery.digest(file)}}}
        self.assertEqual(recovery.checked_asset(lock, self.root, 'input'), file)
        file.write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError, 'damaged'):
            recovery.checked_asset(lock, self.root, 'input')

    def test_zip_traversal_rejected_before_extraction(self):
        file = self.root / 'bad.zip'
        with zipfile.ZipFile(file, 'w') as archive:
            archive.writestr('safe.txt', 'safe')
            archive.writestr('../escaped.txt', 'bad')
        with patch.object(recovery, 'run') as run:
            with self.assertRaises(ValueError):
                recovery.extract_zip(file, self.root / 'out')
            run.assert_not_called()
        self.assertFalse((self.root / 'escaped.txt').exists())

    def test_zip_link_escape_rejected(self):
        file = self.root / 'link.zip'
        with zipfile.ZipFile(file, 'w') as archive:
            member = zipfile.ZipInfo('app/link')
            member.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(member, '../../outside')
        with self.assertRaises(ValueError):
            recovery.extract_zip(file, self.root / 'out')

    def test_tar_traversal_rejected_before_writing(self):
        file = self.root / 'bad.tar'
        with tarfile.open(file, 'w') as archive:
            for name in ['safe.txt', '/tmp/escaped.txt']:
                member = tarfile.TarInfo(name)
                member.size = 1
                archive.addfile(member, io.BytesIO(b'x'))
        destination = self.root / 'out'
        with self.assertRaises(ValueError):
            recovery.extract_tar(file, destination)
        self.assertFalse(destination.exists())

    def test_archive_cannot_write_under_its_symlink(self):
        file = self.root / 'nested.tar'
        with tarfile.open(file, 'w') as archive:
            link = tarfile.TarInfo('directory/alias')
            link.type = tarfile.SYMTYPE
            link.linkname = '..'
            archive.addfile(link)
            child = tarfile.TarInfo('directory/alias/file')
            child.size = 1
            archive.addfile(child, io.BytesIO(b'x'))
        with self.assertRaisesRegex(ValueError, 'nested under a link'):
            recovery.extract_tar(file, self.root / 'out')

    def test_existing_destination_link_rejected(self):
        destination = self.root / 'out'
        destination.mkdir()
        (destination / 'link').symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'destination contains a symlink'):
            recovery.safe_layout([('link/file', False)], destination)

    def test_normal_framework_links_are_supported(self):
        recovery.safe_link('Qt.framework/Versions/Current', 'A')
        recovery.safe_link('Qt.framework/Qt', 'Versions/Current/Qt')
        recovery.safe_layout([('Qt.framework/Versions/A/Qt', False),
                              ('Qt.framework/Versions/Current', True),
                              ('Qt.framework/Qt', True)], self.root)

    def test_restore_refuses_existing_files(self):
        file = self.root / 'keep.txt'
        file.write_text('keep')
        with self.assertRaisesRegex(RuntimeError, 'must be empty'):
            recovery.restore({}, argparse.Namespace(output=self.root))
        self.assertEqual(file.read_text(), 'keep')

    def test_wrong_patched_source_is_rejected(self):
        file = self.root / 'sources/driver/main.c'
        file.parent.mkdir(parents=True)
        file.write_text('different code')
        lock = {'projects': {'driver': {'expected_sources': {'main.c': hashlib.sha256(b'validated code').hexdigest()}}}}
        with self.assertRaisesRegex(RuntimeError, 'differs from tested code'):
            recovery.verify_sources(lock, self.root)

    def test_manifest_has_complete_locked_inputs(self):
        lock = recovery.load_lock()
        self.assertEqual(set(lock['applications']), {'sdrpp', 'brown', 'ce', 'sdrangel'})
        for variant in lock['applications']:
            for prefix in ['original-', 'ready-', 'previous-']:
                self.assertIn(prefix + variant, lock['assets'])
        for key in ['sources', 'sdk']:
            self.assertIn(key, lock['assets'])
        for record in lock['assets'].values():
            self.assertEqual(len(record['sha256']), 64)
            self.assertGreater(record['bytes'], 0)
            self.assertEqual(Path(record['filename']).name, record['filename'])
            self.assertNotIn(record['kind'], {'personal-settings', 'work-history'})
        for project in lock['projects'].values():
            self.assertEqual(len(project['commit']), 40)
            for patch_name in project['patches']:
                self.assertTrue((ROOT / 'patches' / patch_name).is_file())
        config = json.loads((ROOT / 'recovery/defaults/config.json').read_text())
        self.assertEqual(config['source'], 'SoapySDR')
        self.assertFalse(any('meteor' in name.lower() or 'atv' in name.lower()
                             for name in config['moduleInstances']))


if __name__ == '__main__':
    unittest.main()
