"""Opt-in live feedback benchmark on correct/partial/incorrect reference answers."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from core import MODELS,Question,evaluate,GenerationError
ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--limit',type=int,default=1,help='Number of questions; three API calls per question.')
parser.add_argument('--live',action='store_true')
args=parser.parse_args()
if not args.live:raise SystemExit('No calls made. Add --live to run with your private .env key.')
load_dotenv(ROOT.parent/'.env')
key=os.getenv('GROQ_API_KEY','').strip()
if not key:raise SystemExit('No Groq key found in .env. No calls made.')
cases=json.loads((ROOT/'grounded_questions.json').read_text())
output=ROOT/'live_results';output.mkdir(exist_ok=True)
results=[]
for case in cases[:max(1,min(args.limit,len(cases)))]:
    for label,answer in case['answers'].items():
        start=time.monotonic()
        row={'question':case['id'],'answer_label':label,'source_url':case['source_url']}
        try:
            feedback=evaluate(Question.model_validate(case['question']),answer,key,MODELS[0])
            row.update(status='completed',score=sum(c.score for c in feedback.criteria),feedback=feedback.model_dump())
        except GenerationError as e:row.update(status='failed',error=str(e))
        row['seconds']=round(time.monotonic()-start,2);results.append(row)
        # Checkpoint each result; interruptions do not discard earlier calls.
        (output/'answer_feedback_results.json').write_text(json.dumps(results,indent=2))
print(f'Saved {len(results)} results. Human review is required: completion and exact quotes do not establish scoring accuracy.')
