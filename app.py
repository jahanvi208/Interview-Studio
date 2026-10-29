import json
import os
import sqlite3
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv
from pydantic import ValidationError
from core import MODELS, Request, InterviewPack, Question, generate, evaluate, GenerationError, markdown_export
import storage
from session_tools import import_backup, replace_question
from reports import pdf_export

load_dotenv(Path(__file__).resolve().parent / '.env', override=True)
KEY = os.getenv('GROQ_API_KEY', '').strip()
st.set_page_config(page_title='Interview Studio', page_icon='🎯', layout='wide')
st.markdown('''<style>.block-container{max-width:1120px;padding-top:5rem}
h1{letter-spacing:-1px}[data-testid="stMetric"]{border:1px solid #7c8ca344;border-radius:12px;padding:16px}</style>''', unsafe_allow_html=True)

def persist(session):
    storage.save(session)

def show_error(e):
    if isinstance(e, GenerationError): st.error(str(e))
    elif isinstance(e, sqlite3.Error): st.error('Could not save locally. Check that the data folder is writable and has disk space.')
    elif isinstance(e, ValidationError): st.error('Input or saved session is invalid. Check your role and input limits.')
    else: st.error('The operation could not complete. Your saved session is preserved. Please retry.')

with st.sidebar:
    st.title('🎯 Interview Studio')
    st.caption('Question design · Practice · Feedback')
    model = st.selectbox('Generation model', MODELS)
    st.caption('Local API configuration ready' if KEY else 'API not configured: add GROQ_API_KEY to .env beside app.py and restart.')
    st.divider()
    st.subheader('Saved interviews')
    try:
        rows = storage.list_sessions()
        options = {r[0]: f'{r[1]} · {r[2][:16]} UTC · {r[0][:6]}' for r in rows}
        selected = st.selectbox('Choose session', list(options), format_func=options.get) if rows else None
        if selected and st.button('Open saved interview', use_container_width=True):
            loaded = storage.load(selected)
            if loaded:
                Request.model_validate(loaded['request']); InterviewPack.model_validate(loaded['pack'])
                st.session_state['active'] = loaded
                # Saved answers take precedence over stale widget state when reopening.
                for k in list(st.session_state):
                    if k.startswith('answer_'): del st.session_state[k]
                st.rerun()
        if selected:
            confirm = st.checkbox('Confirm deletion of selected saved interview')
            if st.button('Delete selected', disabled=not confirm):
                storage.delete(selected)
                if st.session_state.get('active',{}).get('id') == selected:
                    del st.session_state['active']
                st.rerun()
        if not rows: st.caption('Generated interviews will appear here automatically.')
    except (sqlite3.Error, ValueError, KeyError) as e: show_error(e)
    with st.expander('Restore a JSON backup'):
        backup = st.file_uploader('Interview session JSON', type=['json'], help='Imports a new copy; existing sessions are preserved.')
        if st.button('Restore as new interview', disabled=backup is None):
            try:
                restored = import_backup(backup.getvalue())
                persist(restored)
                st.session_state['active'] = restored
                st.rerun()
            except Exception as e: show_error(e)
    st.divider()
    st.caption('Local use only. Saved sessions contain your JD, answers and feedback in data/interviews.sqlite3. API keys are never saved there. Inputs are sent to Groq for generation or feedback.')

st.caption('INTERVIEW DESIGN & PRACTICE WORKSPACE')
st.title('Better questions. Measurable practice.')
st.write('Generate a role-specific interview, practise your answers, and get feedback tied to a clear scoring rubric.')
with st.expander('Create a new interview', expanded='active' not in st.session_state):
    with st.form('new'):
        c1,c2=st.columns(2)
        role=c1.text_input('Target role','AI Engineer', max_chars=120)
        level=c2.selectbox('Experience',['Intern / Fresher','Junior','Mid-level','Senior'])
        a,b,c=st.columns(3)
        kind=a.selectbox('Interview type',['Mixed','Technical','Behavioral','Scenario-based'])
        difficulty=b.selectbox('Difficulty',['Mixed','Easy','Moderate','Hard'])
        count=c.slider('Questions per batch',1,5,3)
        skills=st.text_input('Skills to focus on',placeholder='Python, RAG, SQL, LLM evaluation',max_chars=600)
        jd=st.text_area('Job description (optional)',max_chars=6000,height=130)
        submitted=st.form_submit_button('Generate new interview',type='primary')
    if submitted:
        try:
            req=Request(role=role,experience=level,interview_type=kind,difficulty=difficulty,skills=skills,job_description=jd,count=count)
            with st.spinner('Generating and validating interview…'):
                pack=generate(req,KEY,model)
            session=storage.new_session(req,model,pack)
            persist(session)
            st.session_state['active']=session
            st.rerun()
        except Exception as e: show_error(e)

if 'active' not in st.session_state:
    st.info('Create an interview or reopen one from the sidebar. Your Groq key loads from .env; there is no key input on this page.')
    st.stop()
session=st.session_state['active']
pack=InterviewPack.model_validate(session['pack'])
req=Request.model_validate(session['request'])
st.subheader(pack.title)
st.caption(f"{req.role} · {req.experience} · {session['model']} · Automatically saved locally")
st.write(pack.role_summary)
a,b,c=st.columns(3)
a.metric('Questions',len(pack.questions)); b.metric('Suggested minutes',sum(q.minutes for q in pack.questions))
feedback_values=list(session['feedback'].values())
c.metric('Average practice score',f"{sum(sum(c['score'] for c in f['criteria']) for f in feedback_values)/len(feedback_values):.1f}/10" if feedback_values else 'Not evaluated')
st.caption('AI feedback is advisory. Review technical accuracy; scores are not a validated measure of hiring suitability.')
with st.expander('Interview settings and assumptions'):
    st.write(f'Skills: {req.skills or "Inferred from role"} · Type: {req.interview_type} · Difficulty: {req.difficulty}')
    for assumption in pack.assumptions: st.write('- '+assumption)

with st.container(border=True):
    left,right=st.columns([1,2])
    more=left.selectbox('Additional questions',[1,2,3,4,5],index=2)
    right.caption('Uses the saved role, skills and job description above. Existing questions, answers and feedback stay in this session. Maximum 30 questions per session.')
    if st.button(f'Generate {more} more',disabled=len(pack.questions)+more>30):
        try:
            with st.spinner('Generating new questions and checking for repeats…'):
                addition=generate(req.model_copy(update={'count':more}),KEY,session['model'],previous=pack.questions)
            updated={**session,'pack':{**session['pack'],'questions':session['pack']['questions']+[q.model_dump() for q in addition.questions]}}
            persist(updated); st.session_state['active']=updated; st.rerun()
        except Exception as e: show_error(e)

practice=st.toggle('Practice mode — hide answer guides',value=True)
search=st.text_input('Search this interview',placeholder='Find a question or competency, e.g. SQL', max_chars=200)
visible=[(i,q) for i,q in enumerate(pack.questions) if search.casefold() in (q.question+' '+q.competency).casefold()]
if search: st.caption(f'{len(visible)} of {len(pack.questions)} questions match. Exports still include the complete interview.')
if not visible: st.info('No matching questions. Clear the search to show all questions.')
for i,q in visible:
    idx=str(i)
    with st.expander(f'Q{i+1} · {q.competency} · {q.difficulty}',expanded=i==0):
        st.subheader(q.question); st.caption(f'{q.kind} · {q.minutes} minutes')
        if not practice:
            st.markdown('**Expected answer / evidence**');st.write(q.expected_answer)
            st.markdown('**Follow-up probes**')
            for f in q.follow_ups: st.write('- '+f)
            st.table([{'Criterion':c.name,'Max':c.points,'Zero credit':c.zero,'Partial credit':c.partial,'Full credit':c.full} for c in q.rubric])
        with st.expander('Replace this question'):
            st.caption('Generates a different question at the same type and difficulty. Only this question’s saved answer and feedback are cleared after success.')
            confirm_replace=st.checkbox('Replace this question and clear its answer',key=f"confirm_{session['id']}_{i}")
            if st.button('Generate replacement',key=f'replace_{i}',disabled=not confirm_replace):
                try:
                    with st.spinner('Generating a replacement and checking for repeats…'):
                        updated=replace_question(session,i,KEY)
                    persist(updated)
                    st.session_state['active']=updated
                    st.session_state.pop(f"answer_{session['id']}_{i}",None)
                    st.session_state.pop(f"confirm_{session['id']}_{i}",None)
                    st.rerun()
                except Exception as e:show_error(e)
        widget=f"answer_{session['id']}_{i}"
        answer=st.text_area('Your answer',value=session['answers'].get(idx,''),key=widget,max_chars=6000,height=150)
        a,b=st.columns(2)
        if a.button('Save answer',key=f'save_{i}'):
            try:
                updated={**session,'answers':{**session['answers'],idx:answer},'feedback':dict(session['feedback'])}
                if answer != session['answers'].get(idx,''): updated['feedback'].pop(idx,None)
                persist(updated);st.session_state['active']=updated;st.rerun()
            except Exception as e: show_error(e)
        if b.button('Evaluate answer',key=f'eval_{i}',type='primary'):
            try:
                with st.spinner('Evaluating against the rubric…'):
                    feedback=evaluate(q,answer,KEY,session['model'])
                updated={**session,'answers':{**session['answers'],idx:answer},'feedback':{**session['feedback'],idx:feedback.model_dump()}}
                persist(updated);st.session_state['active']=updated;st.rerun()
            except Exception as e: show_error(e)
        if answer != session['answers'].get(idx,''): st.caption('Unsaved edits. Save or evaluate to keep them. Previously saved feedback applies only to the saved answer.')
        f=session['feedback'].get(idx)
        if f and answer == session['answers'].get(idx,''):
            st.markdown(f"**AI practice feedback: {sum(c['score'] for c in f['criteria'])}/10**")
            st.write(f['summary'])
            for result in sorted(f['criteria'],key=lambda c:c['criterion_index']):
                criterion=q.rubric[result['criterion_index']]
                st.markdown(f"**{criterion.name}: {result['score']}/{criterion.points}**")
                st.write(result['explanation'])
                if result['evidence_quote']: st.text('Answer evidence: '+result['evidence_quote'])
            for label,field in [('Strengths','strengths'),('Missing points','missing_points'),('Practice next','improvement_plan')]:
                st.markdown('**'+label+'**')
                for item in f[field]:st.write('- '+item)
            with st.expander('Improved answer example'):st.write(f['improved_answer'])

st.divider();st.subheader('Export your interview')
st.caption('Downloads are optional. Sessions are already saved locally. PDF options let you share questions without revealing answer guides or personal practice data.')
a,b=st.columns(2)
include_guides=a.checkbox('Include answer guides and rubrics',value=True)
include_practice=b.checkbox('Include saved practice answers and AI feedback',value=False)
if st.button('Prepare PDF report'):
    try:
        st.session_state['pdf']=(session['id'],json.dumps(session,sort_keys=True),include_guides,include_practice,pdf_export(session,include_guides,include_practice))
    except Exception as e:show_error(e)
pdf=st.session_state.get('pdf')
if pdf and pdf[:4]==(session['id'],json.dumps(session,sort_keys=True),include_guides,include_practice):
    st.download_button('Download PDF report',pdf[4],'interview_report.pdf','application/pdf')
with st.expander('Other export formats'):
    st.caption('These exports contain the complete answer guides; JSON also includes saved practice answers and feedback.')
    st.download_button('Download Markdown',markdown_export(pack,req),'interview_pack.md','text/markdown')
    st.download_button('Download JSON',json.dumps(session,indent=2),'interview_session.json','application/json')
