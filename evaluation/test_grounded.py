"""Validate source-backed fixtures and execute selected reference facts locally."""
import json
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Question
cases=json.loads((Path(__file__).parent/'grounded_questions.json').read_text())
for c in cases:
    q=Question.model_validate(c['question'])
    assert len(q.rubric)==3 and sum(r.points for r in q.rubric)==10
    assert all(v.strip() for v in c['answers'].values())
    assert c['source_url'].startswith('https://')
checks={}
checks['missing_default']=({}.get('timeout',30)==30)
checks['existing_none']=({'timeout':None}.get('timeout',30) is None)
checks['ordered_dedup']=(list(dict.fromkeys([3,1,3,2]))==[3,1,2])
g=(x*x for x in range(3));list(g)
checks['generator_exhausted']=(list(g)==[])
checks['precision']=(15/(15+5)==.75)
checks['recall']=(12/(12+8)==.6)
db=sqlite3.connect(':memory:')
db.execute('CREATE TABLE items(title TEXT)')
title="x' OR 1=1 --";db.execute('INSERT INTO items VALUES(?)',(title,))
checks['bound_quote_value']=(db.execute('SELECT title FROM items WHERE title=?',(title,)).fetchone()[0]==title)
with db:db.execute('SELECT 1')
checks['context_does_not_close']=(db.execute('SELECT 1').fetchone()[0]==1)
db.close()
assert all(checks.values())
result={'fixture_count':len(cases),'fixture_validation':'pass','executable_reference_checks':checks,
        'live_model_evaluation':'not run: no key in build workspace','company_question_provenance':'not claimed'}
(Path(__file__).parent/'grounded_checks.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
