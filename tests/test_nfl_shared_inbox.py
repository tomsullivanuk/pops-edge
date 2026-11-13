import tempfile
import unittest
from pathlib import Path

from nfl_refresh import Workflow


class SharedInboxTests(unittest.TestCase):
    def test_reads_shared_files_without_moving_archives_or_originals(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inbox = root/'com~apple~CloudDocs/PopsEdge/Downloads/NFL'
            inbox.mkdir(parents=True)
            original = inbox/'activity.csv'
            original.write_bytes(b'original export')
            workflow = Workflow(root/'runtime', inbox)
            state = workflow.catalog()
            self.assertTrue(state['input_folder']['available'])
            self.assertEqual(state['input_folder']['source'], 'icloud')
            self.assertEqual(state['input_folder']['label'], 'iCloud Drive / PopsEdge/Downloads/NFL')
            self.assertEqual(workflow.data, (root/'runtime/Data/NFL').resolve())
            selected = state['files'][0]
            spec = {key: selected[key] for key in ('id', 'fingerprint')}
            self.assertEqual(workflow.file_bytes(spec, '.csv')[0], b'original export')
            original.write_bytes(b'changed export')
            with self.assertRaisesRegex(ValueError, 'changed'):
                workflow.file_bytes(spec, '.csv')
            self.assertEqual(original.read_bytes(), b'changed export')
            self.assertFalse((workflow.data/'refreshes').exists())

    def test_missing_shared_folder_has_visible_failure_without_fallback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            inbox = root/'missing/NFL'
            workflow = Workflow(root/'runtime', inbox)
            state = workflow.catalog()
            self.assertFalse(state['input_folder']['available'])
            self.assertIn('Cannot read', state['input_folder']['message'])
            self.assertEqual(state['files'], [])
            self.assertFalse(inbox.exists())
            self.assertFalse((root/'runtime/Downloads/NFL').exists())

    def test_unreadable_file_does_not_leave_partial_selectable_catalog(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as d:
            workflow = Workflow(d)
            (workflow.inbox/'activity.csv').write_bytes(b'export')
            with patch.object(Path, 'read_bytes', side_effect=PermissionError('denied')):
                state = workflow.catalog()
            self.assertFalse(state['input_folder']['available'])
            self.assertEqual(state['files'], [])
            self.assertEqual(workflow.files, {})

    def test_empty_folder_and_symlink_are_not_selected(self):
        with tempfile.TemporaryDirectory() as d:
            workflow = Workflow(d)
            (Path(d)/'elsewhere.csv').write_bytes(b'export')
            (workflow.inbox/'linked.csv').symlink_to(Path(d)/'elsewhere.csv')
            state = workflow.catalog()
            self.assertTrue(state['input_folder']['available'])
            self.assertIn('No Excel or CSV files', state['input_folder']['message'])
            self.assertEqual(state['files'], [])
