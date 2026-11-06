"""Verify public example inputs, assets and source data through spring upgrades."""
import argparse
import hashlib
import json
from pathlib import Path
from .check_material_upgrade import load
from .menu_timing import TIMING_SUFFIX

def compare(before,after):
    old_doc,old,old_assets,_=load(before)
    new_doc,new,new_assets,size=load(after)
    if 'targets' in old_doc:
        assert old_doc['targets'][0]==new_doc['targets'][0] and old_doc['monitors']==new_doc['monitors']
    assert all(new_assets.get(k)==v for k,v in old_assets.items())
    old_lists={v[0]:v[1] for v in old['lists'].values()}
    new_lists={v[0]:v[1] for v in new['lists'].values()}
    for name in ('Original RGB','Grid RGB','LG grid rows','LG grid pixels','matBlurPhoto','matBlurGrid','UI artwork paths'):
        assert old_lists[name]==new_lists[name],name
    examples=[]
    for key,b in old['blocks'].items():
        if not isinstance(b,dict) or b['opcode']!='procedures_call':continue
        code=b['mutation']['proccode']
        if not code.startswith(('Glass %s ','Menu %s ','Button %s ','Background %s ')):continue
        top=key
        while old['blocks'][top]['parent']:
            top=old['blocks'][top]['parent']
        if old['blocks'][top]['opcode']=='procedures_definition':continue
        current=new['blocks'][key]
        expected=code
        if code.startswith('Menu ') and not code.endswith(TIMING_SUFFIX):
            expected+=TIMING_SUFFIX
        if code.startswith('Button ') and not code.endswith(' bounce %s') and current['mutation']['proccode'].endswith(' bounce %s'):
            expected+=' bounce %s'
        assert current['mutation']['proccode']==expected
        ids=json.loads(b['mutation']['argumentids'])
        assert json.loads(current['mutation']['argumentids'])[:len(ids)]==ids
        assert all(b['inputs'][i]==current['inputs'][i] for i in ids),code
        examples.append(code.split()[0])
    assert size<5_000_000 and 'Menu' in examples
    return dict(inputSHA256=hashlib.sha256(before.read_bytes()).hexdigest(),resultSHA256=hashlib.sha256(after.read_bytes()).hexdigest(),
                originalAssets=len(old_assets),allAssetsAndBackgroundsUnchanged=True,publicCallsWithPriorBindings=examples,jsonBytes=size)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for f in ('previous','current','old_component','component','report'):p.add_argument(f,type=Path)
    a=p.parse_args()
    a.report.write_text(json.dumps([compare(a.previous,a.current),compare(a.old_component,a.component)],indent=2)+'\n')
