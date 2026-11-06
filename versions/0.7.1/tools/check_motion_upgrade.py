"""Validate archive preservation and lossless source-image conversion for 0.6.0."""
import argparse
import hashlib
import json
from pathlib import Path
from .check_material_upgrade import load


def inspect(before, after):
    old_doc, old, assets, _ = load(before)
    new_doc, new, current_assets, size = load(after)
    assert assets == current_assets
    if 'targets' in old_doc:
        assert old_doc['targets'][0] == new_doc['targets'][0]
        assert old_doc['monitors'] == new_doc['monitors']
    lists = lambda t: {n:a for n,a in t['lists'].values()}
    src, dst = lists(old), lists(new)
    assert src['Original RGB'] == dst['Original RGB']
    assert not dst['Grid RGB']
    rows, pixels = dst['LG grid rows'], dst['LG grid pixels']
    reconstructed=[p for row in rows for p in pixels[(row-1)*480:row*480]]
    assert len(rows)==360 and reconstructed == src['Grid RGB']
    assert all(src[n]==dst[n] for n in ('matBlurPhoto','matBlurGrid','matLevelRadius','matActiveBank'))
    calls = []
    for key,call in old['blocks'].items():
        if not isinstance(call,dict) or call['opcode']!='procedures_call':continue
        code=call['mutation']['proccode']
        if not code.startswith(('Menu %s ','Background %s ','Button %s ','Glass %s ')):continue
        parent=key
        while old['blocks'][parent]['parent']:parent=old['blocks'][parent]['parent']
        if old['blocks'][parent]['opcode']=='procedures_definition':continue
        updated=new['blocks'][key]
        new_code=updated['mutation']['proccode']
        if code.startswith('Menu '):assert new_code==code+' alignment %s expanded x %s expanded y %s'
        else:assert new_code==code
        old_ids=json.loads(call['mutation']['argumentids'])
        assert json.loads(updated['mutation']['argumentids'])[:len(old_ids)]==old_ids
        assert all(updated['inputs'][i]==call['inputs'][i] for i in old_ids)
        calls.append(code.split(' ')[0])
    assert 'Menu' in calls and size<5_000_000
    return {'inputSHA256':hashlib.sha256(before.read_bytes()).hexdigest(),
            'resultSHA256':hashlib.sha256(after.read_bytes()).hexdigest(),'jsonBytes':size,
            'allAssetsUnchanged':len(assets),'originalPublicExampleArgumentsPreserved':calls,
            'logicalGridPixelsVerified':len(reconstructed),'uniqueGridRows':len(pixels)//480}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('old_studio','new_studio','old_sprite','new_sprite','report'):parser.add_argument(name,type=Path)
    a=parser.parse_args()
    result=[inspect(a.old_studio,a.new_studio),inspect(a.old_sprite,a.new_sprite)]
    a.report.write_text(json.dumps(result,indent=2)+'\n')
    print('Checked both archives and all 172,800 calibration samples.')
