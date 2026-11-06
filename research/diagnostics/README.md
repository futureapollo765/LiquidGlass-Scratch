# Diagnostic archives — not deliverables

These two intermediate editor-save archives were retained only to diagnose native Scratch/TurboWarp round-trip issues. They are invalid diagnostic snapshots, not usable renderer releases:

- `Roundtrip.sb3`: structural validation found missing reporter input references (`data_itemoflist.INDEX` and `operator_subtract.NUM2`). See `../native_roundtrip_diagnostic.json`.
- `CleanRoundtrip.sb3`: structural validation found calls to a missing `LG shape` custom-procedure definition. See `../native_clean_roundtrip_validation.json`.

The report paths record their original locations before this cleanup. Use `../../LiquidGlass_Studio.sb3` or `../../LiquidGlass_Component.sprite3` for the final renderer. `../../EditorVerified.sb3` is the later valid archive saved through the native editor; it was not moved or modified by this cleanup.
