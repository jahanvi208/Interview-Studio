import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import *
import storage
from reports import pdf_export
from test_core import payload, request

class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.pack=InterviewPack.model_validate(payload())
        self.session=storage.new_session(request(),MODELS[0],self.pack)
    def feedback(self):
        return Feedback(summary='Some evidence.',criteria=[CriterionScore(criterion_index=i,score=1,evidence_quote='use get',explanation='Names an approach.') for i in range(3)],strengths=['Approach'],missing_points=['Example'],improvement_plan=['Add an example.'],improved_answer='Use get with a default.')
    def test_storage_roundtrip_and_delete(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.sqlite3'
            self.session['api_key']='do-not-store'
            self.session['answers']['0']='Use get.'
            storage.save(self.session,p)
            self.assertEqual(storage.load(self.session['id'],p)['answers']['0'],'Use get.')
            self.assertNotIn('do-not-store',p.read_bytes().decode(errors='ignore'))
            storage.save(self.session,p)
            self.assertEqual(len(storage.list_sessions(p)),1)
            self.assertIsNone(storage.load("' OR 1=1 --",p))
            storage.delete(self.session['id'],p)
            self.assertEqual(storage.list_sessions(p),[])
    def test_duplicate_similarity(self):
        self.assertTrue(similar('What is a dictionary?', 'WHAT is a dictionary!'))
        self.assertFalse(similar('How do transactions roll back?', 'Explain Python memory management.'))
    @patch('core._ask')
    def test_append_rejects_previous_and_sends_history(self,mock):
        mock.return_value=self.pack
        with self.assertRaisesRegex(GenerationError,'repeated'):
            generate(request(),'fake',MODELS[0],self.pack.questions)
        self.assertEqual(mock.call_args.args[2]['previous_questions_to_avoid'],[self.pack.questions[0].question])
    def test_feedback_grounding_and_bounds(self):
        answer='I use get with a default.'
        f=self.feedback()
        validate_feedback(f,self.pack.questions[0],answer)
        for mutate in [lambda f:setattr(f.criteria[0],'score',99),
                       lambda f:setattr(f.criteria[0],'evidence_quote','fabricated text'),
                       lambda f:setattr(f.criteria[0],'evidence_quote',''),
                       lambda f:setattr(f.criteria[0],'criterion_index',1)]:
            f=self.feedback();mutate(f)
            with self.assertRaises(GenerationError):validate_feedback(f,self.pack.questions[0],answer)
    def test_empty_answer(self):
        with self.assertRaises(GenerationError):evaluate(self.pack.questions[0],'','fake',MODELS[0])
    def test_pdf_modes(self):
        from pypdf import PdfReader
        from io import BytesIO
        self.session['answers']['0']='PRIVATE_PRACTICE_TEXT'
        questions=''.join(p.extract_text() for p in PdfReader(BytesIO(pdf_export(self.session,False,False))).pages)
        full=''.join(p.extract_text() for p in PdfReader(BytesIO(pdf_export(self.session,True,True))).pages)
        self.assertNotIn('Expected answer / evidence',questions)
        self.assertNotIn('PRIVATE_PRACTICE_TEXT',questions)
        self.assertIn('PRIVATE_PRACTICE_TEXT',full)
        self.assertIn('Scoring rubric',full)
    def test_mixed_requirement(self):
        r=request().model_copy(update={'count':3,'difficulty':'Mixed','interview_type':'Mixed'})
        p=copy.deepcopy(payload())
        p['questions']=[copy.deepcopy(p['questions'][0]) for _ in range(3)]
        for i,q in enumerate(p['questions']):q['question']+=str(i)
        with self.assertRaises(GenerationError):validate_pack(InterviewPack.model_validate(p),r)
    @patch('core._ask')
    def test_valid_append_and_evaluation(self,mock):
        mock.return_value=self.pack
        old=self.pack.questions[0].model_copy(update={'question':'Explain SQL transactions.'})
        self.assertEqual(len(generate(request(),'fake',MODELS[0],[old]).questions),1)
        mock.return_value=self.feedback()
        self.assertEqual(len(evaluate(self.pack.questions[0],'I use get with a default.','fake',MODELS[0]).criteria),3)
