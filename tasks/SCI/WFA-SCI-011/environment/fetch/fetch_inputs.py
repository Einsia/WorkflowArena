#!/usr/bin/env python3
"""Fetch pinned cellular-turnover inputs directly from their upstream publisher.

No upstream workbooks or notebook prose are embedded in this program.
"""
import argparse,hashlib,json,os,re,tempfile,urllib.request,zipfile,io
from pathlib import Path

def sanitize_workbook(name,data):
 if name not in ['Mouse_comparison_data.xlsx','Endothelial_cells_data.xlsx']:return data
 with zipfile.ZipFile(io.BytesIO(data)) as z:parts={n:z.read(n) for n in z.namelist()}
 if name.startswith('Mouse'):
  def freeze(m):
   cell=m.group(0)
   if b'[1]!' not in cell or b'<v>6.6136316326325479</v>' not in cell:raise ValueError('Unexpected upstream external formula')
   return re.sub(rb'<f(?:\s[^>]*)?>.*?</f>',b'',cell)
  parts['xl/worksheets/sheet1.xml'],n=re.subn(rb'<c\b[^>]*\br="C5"[^>]*>.*?</c>',freeze,parts['xl/worksheets/sheet1.xml'])
 else:parts['xl/workbook.xml'],n=re.subn(rb'<definedName\b[^>]*name="dr_p"[^>]*>.*?</definedName>',b'',parts['xl/workbook.xml'])
 if n!=1:raise ValueError('Unexpected upstream workbook structure')
 for key in list(parts):
  if key.startswith('xl/externalLinks/') or key=='xl/calcChain.xml':del parts[key]
 parts['xl/workbook.xml']=re.sub(rb'<externalReferences>.*?</externalReferences>',b'',parts['xl/workbook.xml'])
 parts['xl/_rels/workbook.xml.rels']=re.sub(rb'<Relationship\b[^>]*Type="[^"]*/(?:externalLink|calcChain)"[^>]*/>',b'',parts['xl/_rels/workbook.xml.rels'])
 parts['[Content_Types].xml']=re.sub(rb'<Override\b[^>]*PartName="/xl/(?:externalLinks/[^"]*|calcChain.xml)"[^>]*/>',b'',parts['[Content_Types].xml'])
 result=io.BytesIO()
 with zipfile.ZipFile(result,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for key,value in parts.items():
   info=zipfile.ZipInfo(key,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o600<<16;z.writestr(info,value)
 return result.getvalue()
def fetch(manifest,destination,cache=None):
 destination.mkdir(parents=True,exist_ok=True)
 for row in json.loads(manifest.read_text())['files']:
  target=destination/row['target']
  if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Unsafe destination')
  cached=cache/row['source'] if cache else None
  if cached and cached.exists():data=cached.read_bytes()
  else:
   req=urllib.request.Request(row['url'],headers={'User-Agent':'WorkflowArena-source-preparation/1.0'})
   with urllib.request.urlopen(req,timeout=90) as response:data=response.read()
  if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Upstream input hash mismatch: '+row['source'])
  if row['source'].endswith('.ipynb'):
   obj=json.loads(data)
   value='<!-- method notes (prose only; code removed) -->\n\n'+'\n\n'.join(''.join(c['source']) for c in obj['cells'] if c['cell_type']=='markdown')+'\n'
   value=value.replace('Sender','[author]').replace('Milo','[author]');data=value.encode()
  else:data=sanitize_workbook(row['source'],data)
  target.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as tmp:tmp.write(data);tmpname=tmp.name
  os.replace(tmpname,target)
  print('Prepared',row['target'])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--cache-dir',type=Path);a=p.parse_args();fetch(a.manifest,a.destination,a.cache_dir)
