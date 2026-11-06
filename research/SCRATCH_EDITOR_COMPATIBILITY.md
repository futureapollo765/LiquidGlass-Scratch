# Vanilla Scratch editor compatibility investigation

Investigation of the reported palette collapse / blocks gathered at the upper left when importing 0.2.1. The official Scratch editor reproduction in Chrome established a specific cause, described first. The earlier candidate causes below are retained as research context and are not the diagnosis.

## Confirmed cause and minimal fix

The first editor exception in the live reproduction was `Field ID indicator is contained in block ID. This may cause problems with focus: l_field.` Flyout disposal then failed while reading index `2` of an undefined value; those later errors are a cascade after the initial ID failure.

[Blockly's `Field.setSourceBlock`](https://github.com/RaspberryPiFoundation/blockly/blob/26d7da007bbdcb44afdaa3e9bcd855ad2ff0f4e2/packages/blockly/core/field.ts) explicitly rejects any block ID containing the case-sensitive substring `_field`. [Scratch's `addDataList` and `addDataVariable`](https://github.com/scratchfoundation/scratch-blocks/blob/4dc6b6f36c7cfafee3c2833154ce57531149a69a/src/data_category.ts) deliberately use each variable/list ID as the corresponding palette reporter block ID, so monitor checkboxes stay synchronized. The generated list ID `l_field` therefore becomes an invalid palette block ID. The display name `field` is harmless.

The [Blockly connection constructor](https://github.com/RaspberryPiFoundation/blockly/blob/main/packages/blockly/core/connection.ts) similarly reserves `_connection`. A read-only scan of the original 0.2.1 block, scalar-variable, list, broadcast and comment keys found `l_field` as the sole `_field` match. The implemented minimal fix renames only that internal list ID, consistently in the list definition and every reference. The renderer algorithm, list display name, public API, and geometry remain identical. Broader input-shadow, comment, and prototype changes are unnecessary for this demonstrated cause.

Regression checks should scan IDs for both markers, validate every remapped reference, and reload the resulting project in vanilla Scratch. Native TurboWarp execution was insufficient because its older block editor accepted this ID. **Verification status:** 0.2.3 imported successfully in the official vanilla Scratch editor in Chrome. Motion, Variables, My Blocks (all 12 procedures), and Pen palettes displayed normally; Costumes/Code switching worked. The green flag rendered all three shapes. Saving through Scratch and reopening that saved copy retained the working Control/My Blocks palettes. The original ID exception and flyout error cascade did not recur. See `versions/0.2.3/validation/vanilla_scratch_ui.json` and the round-trip reports.

## Observed in the delivered archive

`LiquidGlass_Studio.sb3` at the start of this investigation is a native TurboWarp save with 2,677 blocks in the Liquid Glass sprite. Its 12 procedure definitions have matching argument IDs/names/defaults and explicit `warp` values. No shadow is a top-level script. The green-flag script is at `(40,40)`; other script coordinates are finite. Its 11 block comments have native numeric positions. These observations rule out several simple malformed-project explanations but do not prove compatibility with the modern editor.

There are 3,093 input tuples of kind 2 (connected block without a fallback shadow), 956 of kind 1, and no kind 3 tuples. Unshadowed value reporters are legal in the VM representation. They are less editable: disconnecting a numeric/text reporter should normally reveal a proper default input, which a kind 3 obscured shadow supplies. Adding correct fallback shadows is a reasonable serialization improvement, but there is no evidence yet that their absence causes this import failure. Boolean sockets and statement stacks should remain shadow-free.

## Most relevant primary evidence

1. [Scratch editor regression tracker #533](https://github.com/scratchfoundation/scratch-editor/issues/533) records the April 2026 Blockly-unfork migration, including disappearing scripts, lost palettes, loose custom-block inputs, and deployed repairs. Its archived symptoms resemble the report, but multiple unrelated faults produced them. A merged repair and a deployed website version are distinct.

2. [Scratch editor #636](https://github.com/scratchfoundation/scratch-editor/issues/636) reports block comments breaking projects in Safari. A [maintainer comment](https://github.com/scratchfoundation/scratch-editor/issues/636#issuecomment-5022722613) identifies browsers lacking `Element.prototype.checkVisibility`. [ScratchCommentBubble](https://github.com/scratchfoundation/scratch-blocks/blob/develop/src/scratch_comment_bubble.ts) extends Blockly's comment view; [Blockly 12 CommentView](https://github.com/RaspberryPiFoundation/blockly/blob/blockly-v12.0.0/core/comments/comment_view.ts) calls `foldoutIcon.checkVisibility()` and `deleteIcon.checkVisibility()` without a feature guard in `calcMinSize`. A console error naming `checkVisibility` makes this a concrete candidate. A comment-free diagnostic copy isolates it without changing renderer behavior.

3. [Scratch Blocks #3547](https://github.com/scratchfoundation/scratch-blocks/pull/3547) repaired missing procedure `warp` attributes causing complete workspace-load failure. A follow-up accepted mixed primitive argument defaults. Our mutations contain explicit warp and string defaults, so this known mechanism does not directly apply.

4. [Scratch Blocks #3560](https://github.com/scratchfoundation/scratch-blocks/pull/3560) describes duplicated shadow IDs and a Blockly XML serialization path that dropped inputs. [Scratch editor #536](https://github.com/scratchfoundation/scratch-editor/pull/536) repairs broken shadow references at load time using an intact peer. [Editor #543](https://github.com/scratchfoundation/scratch-editor/pull/543) prevents root shadows from entering the script list; root shadow XML aborts workspace loading. These explain why runtime-valid projects can fail visually, but current structural checks have not found those defects here.

5. [Scratch Blocks #3653](https://github.com/scratchfoundation/scratch-blocks/issues/3653) describes loose input shapes at the upper left despite working runtime code. Its diagnosed example attached a text input to an if/else block. Our static socket audit found no analogous value/Boolean/statement mismatch. [Issue #3662](https://github.com/scratchfoundation/scratch-blocks/issues/3662) separately records major rendering and memory regressions in large engine sprites; it does not establish an argument-count limit.

## Source compatibility details

The [current official SB3 deserializer](https://github.com/scratchfoundation/scratch-editor/blob/develop/packages/scratch-vm/src/serialization/sb3.js) explicitly converts legacy shadow `procedures_prototype` blocks to non-shadow blocks, clears the parent's old shadow reference, and removes saved prototype argument children for regeneration. The [procedure implementation](https://github.com/scratchfoundation/scratch-blocks/blob/develop/src/blocks/procedures.ts) supports the corresponding mutation-driven reconstruction. The old standard prototype encoding is therefore supported; deleting/changing it speculatively is not a justified fix.

The [GUI workspace loader](https://github.com/scratchfoundation/scratch-editor/blob/develop/packages/scratch-gui/src/containers/blocks.jsx) catches workspace parsing exceptions and permits the VM to continue. Successful green-flag execution alone cannot establish that the block editor imported correctly.

## Earlier diagnostic order (superseded by the captured ID exception)

1. Capture the first live `Workspace Update Error` or rendering exception during vanilla Scratch import, before secondary errors.
2. If it is `checkVisibility`, test an otherwise identical comment-free archive in the same browser. Preserve all explanatory text in the repository guide.
3. If it names mutation attributes or a socket/shadow, repair that specific serialization issue and add a regression check. Numeric/text reporter inputs should use correct obscured shadows; Boolean and statement inputs must not acquire them.
4. If no exception occurs, distinguish slow rendering from invalid input by a minimal one-procedure copy and then the full archive. Reduce large helper stacks only if this isolates the failure.
5. Validate the chosen result in vanilla Scratch by import, sprite/tab switching, visible main script, editable public call, running stage, save, and reopen. Keep this separate from VM execution and TurboWarp validation.

The renderer algorithm is unchanged. The root builder now guards storage IDs against reserved Blockly markers; the repair tool changes only typed ID references in existing archives.
