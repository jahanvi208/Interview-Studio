import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from core import MODELS, InterviewPack
import storage
from test_core import payload, request

class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'nested'/'test.sqlite3'
    def tearDown(self):self.temp.cleanup()
    def session(self):return storage.new_session(request(),MODELS[0],InterviewPack.model_validate(payload()))
    def test_1000_sessions_and_100_updates(self):
        sessions=[self.session() for _ in range(1000)]
        for s in sessions:storage.save(s,self.path)
        for i,s in enumerate(sessions[:100]):
            s['answers']['0']=f'Updated answer {i}'
            storage.save(s,self.path)
        with storage.connect(self.path) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],1000)
        for i,s in enumerate(sessions[:100]):self.assertEqual(storage.load(s['id'],self.path)['answers']['0'],f'Updated answer {i}')
        self.assertEqual(len(storage.list_sessions(self.path)),100)
    def test_parallel_independent_writes(self):
        storage.list_sessions(self.path)
        sessions=[self.session() for _ in range(40)]
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda s:storage.save(s,self.path),sessions))
        self.assertEqual(len(storage.list_sessions(self.path)),40)
    def test_persist_across_process(self):
        s=self.session();storage.save(s,self.path)
        script='import storage,sys,json; print(json.dumps(storage.load(sys.argv[1],sys.argv[2])))'
        output=subprocess.check_output([sys.executable,'-c',script,s['id'],str(self.path)],text=True)
        self.assertEqual(json.loads(output),s)
    def test_transaction_rollback(self):
        storage.list_sessions(self.path)
        with self.assertRaises(RuntimeError):
            with storage.connect(self.path) as db:
                db.execute('INSERT INTO sessions VALUES(?,?,?,?)',('rollback','title','date','{}'))
                raise RuntimeError('Simulated interrupted action')
        self.assertIsNone(storage.load('rollback',self.path))
    def test_connection_is_closed(self):
        with storage.connect(self.path) as db:db.execute('SELECT 1')
        with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
    def test_injection_unicode_and_delete_isolation(self):
        s=self.session();s['pack']['title']="Python — हिंदी ' ; DROP TABLE sessions; --"
        storage.save(s,self.path)
        other=self.session();storage.save(other,self.path)
        self.assertEqual(storage.load(s['id'],self.path)['pack']['title'],s['pack']['title'])
        self.assertIsNone(storage.load("' OR 1=1 --",self.path))
        storage.delete("' OR 1=1 --",self.path)
        self.assertEqual(len(storage.list_sessions(self.path)),2)
        storage.delete(s['id'],self.path)
        self.assertIsNotNone(storage.load(other['id'],self.path))
    def test_integrity_and_key_exclusion(self):
        s=self.session();s['GROQ_API_KEY']='sentinel-secret-not-real';storage.save(s,self.path)
        with storage.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            data=db.execute('SELECT payload FROM sessions').fetchone()[0]
            self.assertNotIn('sentinel-secret-not-real',data)
    def test_source_backed_dataset_roundtrip(self):
        source=Path(__file__).parents[1]/'examples'/'source_backed_session.json'
        from session_tools import import_backup
        session=import_backup(source.read_bytes())
        storage.save(session,self.path)
        loaded=storage.load(session['id'],self.path)
        self.assertEqual(len(loaded['pack']['questions']),12)
        self.assertEqual(loaded,session)
        with storage.connect(self.path) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
