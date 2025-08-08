AI.md

Operating guide for AI when working in Warp on the `zfs-fd` tool.

1) Mission and scope
•  Be a terminal-first engineering assistant.
•  Do the thinking, propose precise steps, show exact commands or full files to paste.
•  Don’t rely on tools that aren’t available in this shell.
•  Default to read-only until I ask you to run. If running is requested: avoid pagers, avoid interactive prompts, and provide safe, non-destructive commands.

2) Hard rules and preferences
•  Use sd for file edits (never sed/awk for line edits I’ll paste). Prefer sd for in-place, readable transforms.
•  Pagers: Always disable (e.g., git --no-pager). If a command may page, pipe to cat.
•  Secrets: Never print or inline; use env vars placeholders like {{FOO_API_KEY}}.
•  Copy-paste blocks: When proposing a new/updated file, provide the entire file in one block, ready to paste.
•  Large tasks: Show progress strategies (rates, ETA, chunking, checkpoints).
•  Non-interactive: Avoid commands that open TUI/less/DB shells; give non-interactive equivalents or instructions.

3) When answering questions vs tasks
•  Questions (how/why/what): Explain succinctly; show example commands, do not execute.
•  Tasks (do/run/fix/generate): Provide the full sequence: plan, commands, and verification. If needed, ask one high-value clarification, not many small ones.

4) Version control and diffs
•  When changing code, give a short rationale, then:
•  If small edits: show sd commands (idempotent and safe).
•  If larger: provide the entire new file (copy-pasteable).
•  Never assume I want you to commit; ask before commit/push.
•  If “recent changes” are requested, suggest safe commands with no pagers:
•  git --no-pager log --oneline -n 20
•  git --no-pager diff --stat HEAD~1..HEAD | cat

5) File editing policy
•  Prefer whole-file replacement blocks for complex edits.
•  For simple edits, use sd with clear patterns:
•  sd 'from-pattern' 'to-replacement' path
•  For multiline replacements, provide a here-doc the user can paste, or a full-file block.
•  Never suggest sed -i or awk one-liners unless explicitly requested.

6) Long-running or large-data workflows
•  Always add progress logging (every N items, rate/sec, elapsed).
•  Offer chunked processing (sampling or partitioning).
•  Provide restartability guidance (temporary files, checkpoints).
•  Use memory-aware patterns (avoid storing giant identical lists when possible).

7) ZFS and filesystem manifest guidance (battle-tested patterns)
•  Snapshot direct-read works: read manifests from .zfs/snapshot for accurate point-in-time listing.
•  Path normalization approach:
•  Backup metadata (FS=ASCII 0x1C fields: dataset, size, mtime, fullpath):
◦  Extract real path after /.zfs/snapshot/<snapshot>/ and combine: normalized = dataset + real_path (ensure slash).
•  Filelist clones:
◦  Replace /storage/tmp/zfs-fd-analysis/ with deep_chll/backup/ (or argument-driven dataset root).
•  Encoding: Always open text with encoding='utf-8', errors='replace'.
•  Progress: Log every 100k lines; compute rate and elapsed.
•  Comparison logic: Use dicts keyed by normalized path; don’t store identical entries to save memory.
•  Output categories:
•  only_in_backup.csv
•  only_in_filelist.csv
•  size_mismatches.csv
•  mtime_mismatches.csv
•  both_mismatches.csv
•  Interpretation heuristics:
•  Size-only mismatches with same mtime: reinstall/package version differences (e.g., google-cloud-sdk).
•  Mtime mismatches: normal if backup is newer; if filelist newer, investigate reinstall/clock drift.
•  1980 timestamps: mtime=0 artifacts; not necessarily corruption.

8) zfs-fd CLI design (template)
•  Arguments:
•  --zpool-root PATH
•  --snapshot NAME
•  --output FILE
•  --run-id ID (write as first header line: # RUN_ID: <ID>)
•  --jobs N (default 4)
•  Header:
•  # RUN_ID, # TIMESTAMP, # ZPOOL_ROOT, # SNAPSHOT_NAME, # JOBS
•  Document delimiter: dataset<FS>size<FS>mtime<FS>fullpath (FS=ASCII 0x1C)
•  Fast scanning pattern:
•  fdfind --type f --no-ignore --hidden . "$snap_path" --exec-batch stat --printf "${dataset}\034%s\034%.0Y\034%n\n"
•  Parallel work units (xargs -P N):
•  Process small datasets whole; split large datasets (e.g., backup/home) by top-level subdirectory.

9) Python analysis patterns (templates)
•  Robust readers:
•  Backup TSV (FS=0x1C): split('\x1c'), skip header, utf-8 errors='replace'.
•  Filelist: split(' ', 2) for size, mtime, path.
•  Normalization helpers:
•  Backup: dataset + real_path (ensure leading slash).
•  Filelist: re.sub(r'^/storage/tmp/zfs-fd-analysis/', 'deep_chll/backup/', path)
•  Comparison:
•  Use dict[path] = {size, mtime, original_path, dataset?}
•  Categorize: only_in_backup, only_in_filelist, size_mismatch, mtime_mismatch, both_mismatch.
•  Reporting:
•  Print totals, show first 5 examples per category, save CSVs.
•  Deeper analysis:
•  Convert mtimes via pd.to_datetime(column, unit='s').
•  Buckets relative to snapshot date.
•  Pattern checks for reinstall paths (google-cloud-sdk, .venv, site-packages, node_modules).

10) Output discipline
•  For long files: provide a single fenced block, copy-pasteable.
•  For commands: no echo to print content; put the content in the assistant message, not the command.
•  For secrets: show placeholders; never instruct to echo secrets.

11) Asking for context
•  If a file is referenced but unknown, ask for a copy-paste of its contents or give a full replacement to paste.
•  If a command fails or we can’t read a file, don’t retry blindly—ask for the piece you need.

12) Error handling and verification
•  After any generated script or command set, include a quick verification snippet:
•  e.g., wc -l outputs, head -n, sample reads, rate metrics.
•  When modifying ETL/parsers, include a tiny sample-run harness before full run.

13) Performance checklist
•  Disable globbing pitfalls; quote variables.
•  Avoid unnecessary subshells; prefer batch operations.
•  Use --exec-batch where available.
•  Ensure concurrency stays within I/O budget (configurable --jobs).
•  Avoid pagers; pipe to cat if needed.

14) Copy/paste templates

14.1) sd-based inline edit (single replace)
•  sd 'from-pattern' 'to-replacement' path/to/file

14.2) Here’s a full-file replacement block
•  Provide a single fenced block, entire file content.

14.3) Long-run progress logging (Python)
•  if processed % 100000 == 0: print(f"... rate, elapsed")

15) What not to do
•  Don’t introduce interactive tools.
•  Don’t suggest sed -i for edits I can do with sd.
•  Don’t assume commit/push/restart unless asked.
•  Don’t dump secrets or ask to paste secrets in cleartext.

16) Memory creation
•  When a technique is validated, propose a memory that captures:
•  Concrete input formats, normalization rules (with examples)
•  Parameters and CLI surface of tools/scripts
•  Performance numbers (rates, durations)
•  Failure mode(s) and how we fixed them
•  How to interpret output categories
•  Keep it implementation-grade, not celebratory.

Appendix A: Known-good zfs-fd skeleton (arguments + parallel + fdfind)
•  Keep a maintained copy of the latest “zfs-fd” script in this repo under scripts/ or tools/.
•  Ensure the header includes the RUN_ID line exactly as: # RUN_ID: <RUN_ID>

Appendix B: Git safe patterns (no pagers)
•  git --no-pager log --oneline -n 20
•  git --no-pager diff --stat | cat
•  git --no-pager show --name-only <sha> | cat

Appendix C: CSV outputs for manifest comparison
•  only_in_backup.csv: path, size, mtime, original_path
•  only_in_filelist.csv: path, size, mtime, original_path
•  size_mismatches.csv: path, backup_size, filelist_size, mtime, backup_original, filelist_original
•  mtime_mismatches.csv: path, size, backup_mtime, filelist_mtime, backup_original, filelist_original
•  both_mismatches.csv: path, backup_size, filelist_size, backup_mtime, filelist_mtime, backup_original, filelist_original