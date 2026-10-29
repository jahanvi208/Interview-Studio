"""Atomic session changes and validation for portable session backups."""
import json
from copy import deepcopy
from uuid import uuid4
from core import (Request, InterviewPack, Feedback, GenerationError, MODELS,
                  validate_pack, validate_feedback, generate)


def import_backup(raw: bytes) -> dict:
    if len(raw) > 1_000_000:
        raise GenerationError('Backup is too large. Maximum size is 1 MB.')
    try:
        data = json.loads(raw)
        req = Request.model_validate(data['request'])
        pack = InterviewPack.model_validate(data['pack'])
        if not 1 <= len(pack.questions) <= 30 or data['model'] not in MODELS:
            raise ValueError('Invalid question count or model')
        validate_pack(pack, req.model_copy(update={'count': len(pack.questions)}))
        answers = data.get('answers', {})
        feedback = data.get('feedback', {})
        if not isinstance(answers, dict) or not isinstance(feedback, dict):
            raise ValueError('Invalid practice records')
        valid_indices = {str(i) for i in range(len(pack.questions))}
        if not set(answers).issubset(valid_indices) or not set(feedback).issubset(valid_indices):
            raise ValueError('Invalid question reference')
        if any(not isinstance(a, str) or len(a) > 6000 for a in answers.values()):
            raise ValueError('Invalid answer')
        clean_feedback = {}
        for idx, value in feedback.items():
            f = validate_feedback(Feedback.model_validate(value), pack.questions[int(idx)], answers.get(idx, ''))
            clean_feedback[idx] = f.model_dump()
        # Always import as a new session. Never trust a supplied database ID or extras.
        return {'id': uuid4().hex, 'request': req.model_dump(), 'model': data['model'],
                'pack': pack.model_dump(), 'answers': answers, 'feedback': clean_feedback}
    except (ValueError, TypeError, KeyError, GenerationError):
        raise GenerationError('Invalid backup. Choose a complete Interview Studio JSON export with valid questions and feedback.') from None


def replace_question(session: dict, index: int, key: str) -> dict:
    pack = InterviewPack.model_validate(session['pack'])
    if not 0 <= index < len(pack.questions):
        raise GenerationError('Question does not exist.')
    old = pack.questions[index]
    req = Request.model_validate(session['request']).model_copy(update={
        'count': 1, 'difficulty': old.difficulty, 'interview_type': old.kind})
    addition = generate(req, key, session['model'], previous=pack.questions)
    updated = deepcopy(session)
    updated['pack']['questions'][index] = addition.questions[0].model_dump()
    updated['answers'].pop(str(index), None)
    updated['feedback'].pop(str(index), None)
    return updated
