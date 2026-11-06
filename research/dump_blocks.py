import json
from pathlib import Path

def dump(t):
 bs=t['blocks']
 def inp(v):
  if v is None:return '???'
  x=v[1] if isinstance(v,list) else v
  if isinstance(x,str):return expr(x)
  if isinstance(x,list):return str(x[1])
  return str(x)
 def expr(i):
  if i not in bs:return str(i)
  b=bs[i]
  if isinstance(b,list):return str(b[1])
  op=b['opcode']; f={k:v[0] for k,v in b.get('fields',{}).items()};ins={k:inp(v) for k,v in b.get('inputs',{}).items() if not k.startswith('SUBSTACK')}
  if op.startswith('argument_reporter'):return '$'+f['VALUE']
  if op in ['data_variable','data_listcontents']:return list(f.values())[0]
  if op=='procedures_call':return b['mutation']['proccode']+' '+str(list(ins.values()))
  if op=='data_itemoflist':return f['LIST']+'['+ins['INDEX']+']'
  ops={'operator_add':'+','operator_subtract':'-','operator_multiply':'*','operator_divide':'/','operator_lt':'<','operator_gt':'>','operator_equals':'=','operator_and':'and','operator_or':'or','operator_mod':'mod'}
  if op in ops:return '('+(' '+ops[op]+' ').join(ins.values())+')'
  if op=='operator_mathop':return f['OPERATOR']+'('+ins['NUM']+')'
  return op.replace('data_','').replace('operator_','')+'('+', '.join(str(k)+'='+str(v) for k,v in (f|ins).items())+')'
 def stack(i,d=0):
  out=[]
  while i:
   b=bs[i];out.append('  '*d+expr(i))
   for k,v in b.get('inputs',{}).items():
    if k.startswith('SUBSTACK'):out.append('  '*d+k);out.extend(stack(v[1],d+1))
   i=b.get('next')
  return out
 out=[]
 for i,b in bs.items():
  if isinstance(b,dict) and b.get('topLevel'):
   if b['opcode']=='procedures_definition':
    proto=bs[b['inputs']['custom_block'][1]];out.append('\nDEFINE '+proto['mutation']['proccode']+' '+proto['mutation']['argumentnames']);out+=stack(b.get('next'))
   elif b['opcode'].startswith('event_'):out.append('\nHAT');out+=stack(i)
 return '\n'.join(out)
for p in Path('research').glob('reference_*.json'):
 j=json.loads(p.read_text());s='\n'.join('\nTARGET '+t['name']+'\n'+dump(t) for t in j['targets']);p.with_suffix('.txt').write_text(s)
