import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

import scripts.failure_experiment as failure_experiment
from agents.tools import check_local_site
from agents.core import validate


class TestProject(unittest.TestCase):
    def test_site(self):
        self.assertTrue(check_local_site()['ok'])
    def test_missing_fields_fail(self):
        with self.assertRaises(ValueError): validate('requirements', {'summary':'x'})
    def test_valid_requirements(self):
        output={'summary':'x','pages':['a','b','c','d','e'],'services':[], 'security_requirements':[], 'questions':[]}
        self.assertEqual(validate('requirements',output),output)

    def run_probe_check(self, status, response=None, request_error=None):
        probe_id = 'a' * 32
        state = {
            'probe_id': probe_id,
            'bucket': failure_experiment.EXPECTED_BUCKET,
            'key': f'{failure_experiment.KEY_PREFIX}{probe_id}.txt',
            'content': f'CSCE 412 recovery probe {probe_id}\n',
            'status': status,
        }
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / 'probe-state.json'
            state_path.write_text(json.dumps(state), encoding='utf-8')
            with patch.object(failure_experiment, 'STATE_PATH', state_path):
                with patch.dict(os.environ, {'SITE_URL': 'https://csce412hiya.link'}):
                    with patch.object(failure_experiment, 'record'):
                        with patch.object(failure_experiment.requests, 'get', return_value=response,
                                          side_effect=request_error) as get:
                            result = failure_experiment.check_probe()
                            get.assert_called_once()
                            return result

    def test_seeded_probe_requires_matching_https_content(self):
        probe_id = 'a' * 32
        response = Mock(
            status_code=200,
            url=f'https://csce412hiya.link/{failure_experiment.KEY_PREFIX}{probe_id}.txt',
            ok=True,
            text=f'CSCE 412 recovery probe {probe_id}\n',
        )
        result = self.run_probe_check('seeded', response=response)
        self.assertTrue(result['available'])
        self.assertTrue(result['ok'])

    def test_missing_probe_is_observed_during_break(self):
        probe_id = 'a' * 32
        response = Mock(
            status_code=403,
            url=f'https://csce412hiya.link/{failure_experiment.KEY_PREFIX}{probe_id}.txt',
            ok=False,
            text='',
        )
        result = self.run_probe_check('broken', response=response)
        self.assertFalse(result['available'])
        self.assertTrue(result['ok'])

    def test_network_error_does_not_count_as_verified_failure(self):
        result = self.run_probe_check('broken', request_error=requests.Timeout('timed out'))
        self.assertFalse(result['ok'])

if __name__=='__main__':unittest.main()
