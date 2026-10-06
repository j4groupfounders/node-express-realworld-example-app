"""Five preregistered route faults. No model/API calls. Always restore original source."""
import pathlib,subprocess,json,os,signal,time
root=pathlib.Path('.')
mutations=[
 ('tags-status','src/app/routes/tag/tag.controller.ts','res.json({ tags });','res.status(201).json({ tags });'),
 ('article-count','src/app/routes/article/article.controller.ts','res.json(result);','res.json({ ...result, articlesCount: -1 });'),
 ('unauthorized-status','src/main.ts','res.status(401).json','res.status(200).json'),
 ('missing-route-status','src/main.ts',"const PORT = process.env.PORT || 3000;","app.get('/j4-missing', (req, res) => res.status(200).json({}));\nconst PORT = process.env.PORT || 3000;"),
 ('login-error-status','src/main.ts','res.status(err.errorCode).json(err.message);',"res.status(req.path === '/api/users/login' ? 200 : err.errorCode).json(err.message);")]
results=[]
for name,file,old,new in mutations:
 p=root/file;original=p.read_text();assert old in original
 dest=root/'seed-evidence'/name;dest.mkdir(parents=True,exist_ok=True)
 server=None
 try:
  p.write_text(original.replace(old,new,1))
  with (dest/'tests.log').open('w') as log:
   test=subprocess.run(['npx','jest','--runInBand','--json','--outputFile='+str(dest/'tests.json')],stdout=log,stderr=subprocess.STDOUT,timeout=100)
  data=json.loads((dest/'tests.json').read_text());assert data['numTotalTests']==27 and data['numRuntimeErrorTestSuites']==0,'test infrastructure failure'
  with (dest/'boot.log').open('w') as log:
   server=subprocess.Popen(['npx','ts-node','--transpile-only','--compiler-options','{"module":"CommonJS"}','src/main.ts'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   with (dest/'probe.log').open('w') as probe:
    check=subprocess.run(['python3','j4_probe.py'],stdout=probe,stderr=subprocess.STDOUT,timeout=90)
   output=(dest/'probe.log').read_text()
   assert 'BOOT FAILED' not in output and 'CHARACTERIZATION DRIFT' in output,'mutation did not produce measured differential'
   pathlib.Path('surface.actual.json').replace(dest/'surface.json')
  results.append(dict(fault=name,project_detected=test.returncode!=0,harness_detected=check.returncode!=0,project_passed=data['numPassedTests'],project_failed=data['numFailedTests']))
 finally:
  p.write_text(original)
  if server:
   os.killpg(server.pid,signal.SIGTERM);server.wait(timeout=15)
  time.sleep(1)
pathlib.Path('seed-results.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
a=sum(r['project_detected'] for r in results);b=sum(r['project_detected'] or r['harness_detected'] for r in results)
assert b>=4 and 5-b<=(5-a)/2
