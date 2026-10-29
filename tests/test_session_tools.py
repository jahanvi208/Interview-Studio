import copy
import json
import unittest
from unittest.mock import patch
from core import InterviewPack, GenerationError, MODELS
from storage import new_session
from session_tools import import_backup, replace_question
from test_core import payload, request

class SessionToolTests(unittest.TestCase):
    def setUp(self):
        self.session=new_session(request(),MODELS[0],InterviewPack.model_validate(payload()))
        self.session['answers']['0']='I use get.'
    def test_import_new_id_and_no_extras(self):
        self.session['api_key']='do-not-keep'
        restored=import_backup(json.dumps(self.session).encode())
        self.assertNotEqual(restored['id'],self.session['id'])
        self.assertEqual(restored['answers'],self.session['answers'])
        self.assertNotIn('api_key',restored)
    def test_reject_invalid_references(self):
        self.session['answers']['88']='Invalid reference'
        with self.assertRaises(GenerationError):import_backup(json.dumps(self.session).encode())
    def test_reject_bad_backup(self):
        for raw in (b'no json',b'[]',b'{}',b'x'*1_000_001):
            with self.assertRaises(GenerationError):import_backup(raw)
    def test_reject_bad_feedback(self):
        self.session['feedback']['0']={'summary':'Invalid'}
        with self.assertRaises(GenerationError):import_backup(json.dumps(self.session).encode())
    @patch('session_tools.generate')
    def test_replace_only_selected_and_no_mutation(self,mock):
        second=copy.deepcopy(self.session['pack']['questions'][0]);second['question']='Explain SQL transaction isolation.'
        self.session['pack']['questions'].append(second)
        self.session['answers']['1']='Preserve this.'
        p=payload();p['questions'][0]['question']='Explain Python generators.'
        mock.return_value=InterviewPack.model_validate(p)
        old=copy.deepcopy(self.session)
        result=replace_question(self.session,0,'fake-key')
        self.assertEqual(self.session,old)
        self.assertNotIn('0',result['answers'])
        self.assertEqual(result['answers']['1'],'Preserve this.')
        self.assertEqual(result['pack']['questions'][1],second)
        self.assertEqual(mock.call_args.args[0].difficulty,'Easy')
        self.assertEqual(len(mock.call_args.kwargs['previous']),2)
    @patch('session_tools.generate',side_effect=GenerationError('Unavailable'))
    def test_failed_replace_preserves_data(self,mock):
        original=copy.deepcopy(self.session)
        with self.assertRaises(GenerationError):replace_question(self.session,0,'fake-key')
        self.assertEqual(self.session,original)
