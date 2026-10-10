"""Copy only the review-page inputs and current baseline files into Vite public/."""
from pathlib import Path
import json
import shutil
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'artifacts/baseline'
public=ROOT/'viewer/public/artifacts/baseline'
public.mkdir(parents=True,exist_ok=True)
manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
needed={'manifest.json','validation.json','parameters.json','assembly.step'}
for part in manifest['parts']:
    needed.update(part['files'].values())
for name in sorted(needed):
    shutil.copyfile(source/name,public/name)
docs=ROOT/'viewer/public/docs';docs.mkdir(parents=True,exist_ok=True)
shutil.copyfile(ROOT/'docs/sources-and-assumptions.md',docs/'sources-and-assumptions.md')
print(json.dumps({'source_revision':manifest['source_revision'],'copied_files':len(needed)+1,
                  'destination':'viewer/public'}))
