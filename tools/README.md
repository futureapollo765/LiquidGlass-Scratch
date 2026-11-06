# Scratch archive and VM verification

These tools verify the generated renderer with no global dependencies or network access.

```sh
python3 tools/validate_sb3.py LiquidGlass_Studio.sb3
node tools/vm_harness.cjs LiquidGlass_Studio.sb3 2
```

`validate_sb3.py` checks ZIP CRCs, embedded asset digests, block references and parents, variable/list references, custom procedure signatures, reserved Blockly ID markers, and that Pen is the only extension. It also rejects detached non-top-level blocks.

`vm_harness.cjs` reads the real VM and storage library embedded in the installed `/Applications/TurboWarp.app`. It exposes only the bundled libraries, with the packaged browser entry disabled. `loadProject()` performs the VM's own SB3 schema validation, deserialization, and extension registration. Runtime commands execute the actual Scratch/TurboWarp primitives. No network extension is used.

The headless runtime has no display/audio renderer. Its absence produces expected “No rendering module present” warnings. Headless tests establish block execution, calculations, state, and compatibility; visual appearance and interactive input must also be tested in TurboWarp Desktop.

From a CommonJS test file:

```js
const h = require('./vm_harness.cjs');
const vm = await h.loadProject(filename, {compiler: false});
h.invoke(vm, 'Liquid Glass', 'Some procedure %s', [42]);
console.log(h.getVariable(vm, 'Liquid Glass', 'result').value);
vm.stopAll();
```

`invoke()` stops other scripts before calling the procedure, executes until that call finishes, and removes its temporary call blocks. `{compiler: true}` tests TurboWarp compilation; the default interpreter more directly checks Scratch execution semantics. `stepFrames(vm, count)` advances the VM without wall-clock delays. Animation based on Scratch's timer therefore needs an explicit clock fixture or real elapsed time in tests.

Primary definitions consulted:

- [Scratch SB3 serializer/deserializer](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/serialization/sb3.js)
- [Scratch custom procedure primitives](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/blocks/scratch3_procedures.js)
- [Scratch native Pen extension](https://github.com/scratchfoundation/scratch-vm/blob/develop/src/extensions/scratch3_pen/index.js)

Native pen transparency accepts `0` (opaque) through `100` (transparent). Setting pen color resets transparency, so the renderer must set transparency after color.

`repair_editor_ids.py` repairs storage IDs containing Blockly's reserved `_field` or `_connection` markers while preserving displayed names, values, blocks, and assets. The current compatibility fix changes only `l_field` and eight list references. It supports both SB3 projects and sprite3 components, verifies equivalence after undoing the ID mapping, and refuses JSON at or above 5,000,000 bytes.

```sh
python3 tools/repair_editor_ids.py input.sb3 fixed.sb3 --report repair.json
```

This palette regression must also be checked in the current vanilla Scratch editor; the older TurboWarp editor and VM can accept an ID that modern Blockly rejects.
