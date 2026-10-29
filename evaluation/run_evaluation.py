"""Offline validator checks by default; explicit --live calls Groq using local key."""
import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
from core import Request, MODELS, generate

ROOT=Path(__file__).resolve().parent

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--live',action='store_true',help='Send dataset prompts to Groq; consumes account quota.')
    parser.add_argument('--limit',type=int,default=3)
    args=parser.parse_args()
    cases=json.loads((ROOT/'cases.json').read_text())
    for case in cases:Request.model_validate(case['request'])
    print(f'{len(cases)} evaluation requests pass input validation.')
    if not args.live:
        print('No live calls made. Use --live --limit 3 to collect model outputs for manual review.');return
    load_dotenv(ROOT.parent/'.env')
    key=os.getenv('GROQ_API_KEY','')
    if not key:raise SystemExit('Configure GROQ_API_KEY in .env first.')
    output=ROOT/'live_results';output.mkdir(exist_ok=True)
    results=[]
    for case in cases[:max(1,args.limit)]:
        start=time.monotonic()
        try:
            pack=generate(Request.model_validate(case['request']),key,MODELS[0])
            (output/(case['id']+'.json')).write_text(pack.model_dump_json(indent=2))
            status='PASS structural checks; human review pending'
        except Exception:
            status='FAIL generation or validation; inspect app/provider limits'
        results.append({'case':case['id'],'status':status,'seconds':round(time.monotonic()-start,2),
                        'relevance_1_to_5':'','difficulty_1_to_5':'','rubric_specificity_1_to_5':'','technical_accuracy_1_to_5':'','notes':''})
    with (output/'review.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=results[0].keys());writer.writeheader();writer.writerows(results)
    print('Results and a blank human-review scorecard saved in evaluation/live_results/. No quality ratings were invented.')
if __name__=='__main__':main()
