# Local copies and GitHub releases

Keep the editable project in this directory and all numbered snapshots under `versions/`. After each completed update, run the relevant checks, review the changed files, and run `sh tools/sync_github.sh "Describe the update"`. The original checkout keeps its own local history. The helper scans a clean export and pushes through the separate `.github-sync` checkout. Keep the original history local and publish only the reviewed Liquid Glass tree to the public GitHub repository. Keep the parent Scratch directory outside both repositories. If Git rejects the push, inspect the remote changes before reconciling them.

Review new images, footage, and embedded Scratch assets for identifying details and metadata before adding their SHA-256 digests to `tools/reviewed_media.sha256`. Keep original device recordings and private scan terms local. Use a GitHub no-reply commit email for publishing.

For a release, save the local numbered snapshot, finish its validation, and update `CHANGELOG.md` and `UPDATE_LOG.txt` before syncing. Commit `VERSION` and the release files together. Check that GitHub published the matching tag and both Scratch downloads. Preserve numbered editor saves as well as the originally released bytes when they differ.
