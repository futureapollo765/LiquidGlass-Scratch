"""Check that migrated public calls keep the user's existing bindings and assets."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def load(path):
    with zipfile.ZipFile(path) as z:
        entry='project.json' if 'project.json' in z.namelist() else 'sprite.json'
        payload=z.read(entry)
        doc=json.loads(payload)
        sprite=next(t for t in doc['targets'] if t['name']=='Liquid Glass') if 'targets' in doc else doc
        assets={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n!=entry}
        return doc,sprite,assets,len(payload)


def check(before,after):
    oldDoc,old,oldAssets,_=load(before)
    newDoc,new,newAssets,newBytes=load(after)
    assert all(newAssets.get(k)==v for k,v in oldAssets.items())
    if 'targets' in oldDoc:
        assert oldDoc['targets'][0]==newDoc['targets'][0], 'Stage was unexpectedly modified'
        assert oldDoc['monitors']==newDoc['monitors']
    for k in ('Original RGB','Grid RGB'):
        find=lambda t:next(v[1] for v in t['lists'].values() if v[0]==k)
        assert find(old)==find(new)
    public=('Glass','Menu','Button','Background')
    examples=[]
    for key,b in old['blocks'].items():
        if not isinstance(b,dict) or b['opcode']!='procedures_call' or b.get('mutation',{}).get('proccode','').split(' ')[0] not in public:
            continue
        # Definitions may intentionally gain a new implementation, but all original
        # user call sites in green-flag scripts and standalone stacks stay attached.
        owner=key
        while owner and old['blocks'][owner].get('parent'):
            owner=old['blocks'][owner]['parent']
        if old['blocks'][owner]['opcode']=='procedures_definition':continue
        curr=new['blocks'][key]
        assert curr['mutation']['proccode'].startswith(b['mutation']['proccode']+' tint color %s')
        ids=json.loads(b['mutation']['argumentids'])
        assert json.loads(curr['mutation']['argumentids'])[:len(ids)]==ids
        changed=[]
        for index,aid in enumerate(ids):
            if b['inputs'][aid]!=curr['inputs'][aid]:
                changed.append(index)
                assert b['mutation']['proccode'].startswith('Menu ') and index==9
                assert curr['inputs'][aid][1][1].startswith(b['inputs'][aid][1][1]+'|Menu finish>')
        examples.append({'id':key,'type':b['mutation']['proccode'].split(' ')[0],'extendedExistingInputs':changed})
    assert newBytes<5_000_000
    return dict(source=str(before),sourceSHA256=hashlib.sha256(before.read_bytes()).hexdigest(),
                delivery=str(after),sha256=hashlib.sha256(after.read_bytes()).hexdigest(),jsonBytes=newBytes,
                sourceAssetsRetained=len(oldAssets),addedAssets=len(newAssets)-len(oldAssets),
                sampledBackgroundsIdentical=True,publicExamples=examples)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('original_studio','studio','original_sprite','sprite','report'):p.add_argument(k,type=Path)
    a=p.parse_args()
    results=[check(a.original_studio,a.studio),check(a.original_sprite,a.sprite)]
    a.report.write_text(json.dumps(results,indent=2)+'\n')
    print([(r['jsonBytes'],len(r['publicExamples'])) for r in results])
