import copy
import functools
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
from streamlit.testing.v1 import AppTest
from core import InterviewPack
import storage
from test_core import payload

class UITests(unittest.TestCase):
    def test_generate_append_save_reopen_and_export(self):
        with tempfile.TemporaryDirectory() as d, ExitStack() as stack:
            for name in ('save','load','list_sessions','delete'):
                stack.enter_context(patch('storage.'+name,functools.partial(getattr(storage,name),path=Path(d)/'test.db')))
            gen=stack.enter_context(patch('core.generate',return_value=InterviewPack.model_validate(payload())))
            at=AppTest.from_file(str(Path(__file__).parents[1]/'app.py')).run()
            self.assertFalse(at.exception)
            next(b for b in at.button if b.label=='Generate new interview').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.metric[0].value,'1')
            p=copy.deepcopy(payload());p['questions'][0]['question']='Explain database transaction isolation.'
            gen.return_value=InterviewPack.model_validate(p)
            next(b for b in at.button if b.label=='Generate 3 more').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.metric[0].value,'2')
            at.text_area[1].set_value('I use get with a default.')
            next(b for b in at.button if b.label=='Save answer').click().run()
            self.assertFalse(at.exception)
            next(b for b in at.button if b.label=='Open saved interview').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.text_area[1].value,'I use get with a default.')
            from core import Feedback
            fb=Feedback(summary='Evidence found.',criteria=[dict(criterion_index=i,score=1,evidence_quote='use get',explanation='Names a method.') for i in range(3)],strengths=['Method'],missing_points=['Example'],improvement_plan=['Add an example.'],improved_answer='Use get with a default.')
            with patch('core.evaluate',return_value=fb):
                next(b for b in at.button if b.label=='Evaluate answer').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.metric[2].value,'3.0/10')
            next(b for b in at.button if b.label=='Prepare PDF report').click().run()
            self.assertFalse(at.exception)
            self.assertTrue(any(x.label=='Download PDF report' for x in at.get('download_button')))

            search=next(t for t in at.text_input if t.label=='Search this interview')
            search.set_value('no_such_topic_123').run()
            self.assertFalse(at.exception)
            self.assertFalse(any(t.label=='Your answer' for t in at.text_area))
            next(t for t in at.text_input if t.label=='Search this interview').set_value('').run()
            next(c for c in at.checkbox if c.label=='Replace this question and clear its answer').check().run()
            replacement=copy.deepcopy(payload())
            replacement['questions'][0]['question']='Explain iterator exhaustion in Python.'
            with patch('session_tools.generate',return_value=InterviewPack.model_validate(replacement)):
                next(b for b in at.button if b.label=='Generate replacement').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.text_area[1].value,'')
            self.assertEqual(at.metric[2].value,'Not evaluated')
