import copy
import json
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch, MagicMock
import httpx
import groq
from core import Request, InterviewPack, GenerationError, validate_pack, generate, markdown_export

def request():
    return Request(role='Python Developer', experience='Junior', difficulty='Easy',
                   interview_type='Technical', skills='Python', job_description='', count=1)

def payload():
    return {'title': 'Python Interview', 'role_summary': 'Test Python fundamentals.',
            'assumptions': ['Junior role'], 'questions': [{
                'question': 'How would you handle a missing dictionary key?',
                'competency': 'Dictionaries', 'difficulty': 'Easy', 'kind': 'Technical',
                'minutes': 5, 'expected_answer': 'Use get, membership checks, or handle KeyError.',
                'follow_ups': ['When would you use get?', 'How does defaultdict differ?'],
                'rubric': [{'name': name, 'points': points, 'zero': 'No usable approach.',
                            'partial': 'Names an approach without explaining behavior.',
                            'full': 'Explains an approach and its behavior with an example.'}
                           for name, points in [('Approach',4),('Behavior',3),('Example',3)]]}]}

class CoreTests(unittest.TestCase):
    def test_valid_and_export(self):
        pack = validate_pack(InterviewPack.model_validate(payload()), request())
        text = markdown_export(pack, request())
        self.assertIn('Full credit:', text)
        self.assertIn('10 points', text)
        self.assertNotIn('GROQ_API_KEY', text)

    def test_semantic_failures(self):
        for mutate in [lambda p: p['questions'][0]['rubric'][0].update(points=2),
                       lambda p: p['questions'][0].update(follow_ups=[]),
                       lambda p: p['questions'][0].update(difficulty='Hard'),
                       lambda p: p['questions'][0].update(question=''),
                       lambda p: p['questions'][0].update(minutes=0)]:
            p = payload(); mutate(p)
            with self.assertRaises(GenerationError):
                validate_pack(InterviewPack.model_validate(p), request())

    def test_duplicate(self):
        p = payload(); p['questions'].append(copy.deepcopy(p['questions'][0]))
        r = request().model_copy(update={'count': 2})
        with self.assertRaises(GenerationError):
            validate_pack(InterviewPack.model_validate(p), r)

    @patch('groq.Groq')
    def test_generation_and_schema(self, mock):
        client = mock.return_value.__enter__.return_value
        client.chat.completions.create.return_value = NS(choices=[NS(
            finish_reason='stop', message=NS(content=json.dumps(payload())))])
        self.assertEqual(len(generate(request(), 'test-key', 'openai/gpt-oss-120b').questions), 1)
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertTrue(kwargs['response_format']['json_schema']['strict'])
        self.assertNotIn('test-key', json.dumps(kwargs))
        for definition in kwargs['response_format']['json_schema']['schema']['$defs'].values():
            self.assertFalse(definition['additionalProperties'])
            self.assertEqual(set(definition['required']), set(definition['properties']))

    @patch('groq.Groq')
    def test_truncation(self, mock):
        mock.return_value.__enter__.return_value.chat.completions.create.return_value = NS(
            choices=[NS(finish_reason='length', message=NS(content='{}'))])
        with self.assertRaisesRegex(GenerationError, 'incomplete'):
            generate(request(), 'test-key', 'openai/gpt-oss-120b')

    @patch('groq.Groq')
    def test_provider_errors_are_safe(self, mock):
        response = httpx.Response(429, request=httpx.Request('POST','https://api.groq.com'))
        client = mock.return_value.__enter__.return_value
        for cls, message in [(groq.RateLimitError, 'limit'), (groq.AuthenticationError, 'key')]:
            client.chat.completions.create.side_effect = cls('secret-test-key', response=response, body=None)
            with self.assertRaises(GenerationError) as caught:
                generate(request(), 'test-key', 'openai/gpt-oss-120b')
            self.assertIn(message, str(caught.exception))
            self.assertNotIn('secret-test-key', str(caught.exception))

if __name__ == '__main__':
    unittest.main()
