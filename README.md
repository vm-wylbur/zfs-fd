# zfs-fd

Fast filesystem discovery for ZFS snapshots. Enumerate millions of files in minutes, not hours.

## tl;dr 

**Problem**: Need to know what files exist in your ZFS backups without mounting snapshots or waiting forever.

**Solution**: `zfs-fd` reads directly from ZFS snapshot directories in parallel, aggregates by directory, and outputs both raw data and summaries.

**Usage**:
```bash
sudo ./zfs-fd my-run-id-2025-01-11
# Outputs: /var/lib/zfs-fd/topdirs-my-run-id-2025-01-11.json
```

**What you get**:
- Compressed TSV with every file's dataset, size, mtime, and path (~100MB for 10M files)
- JSON summary of top directories with file counts and total sizes
- Processing rate: ~190K files/second sustained (13.6M files in 71 seconds with ZFS special vdev)

**Requirements**: Root access, ZFS filesystem, `fdfind`, and about 90 seconds for 13 million files.

## The Journey (or: How I Learned to Stop Over-Engineering and Love the Dumb Solution)

Back in August 2025, I needed to enumerate files in our ZFS backup snapshots for deduplication analysis. Simple problem, right? Just list the files.

Except it wasn't simple. We spent hours trying to use `.zfs/snapshot/` directly but got confused by our backup structure. The `backup/` dataset isn't just a directory - it contains both actual files AND unmounted child datasets (`backup/home`, `backup/zsd`). Each dataset has its own snapshots. You can't just point `find` at the root and expect it to work.

So we gave up and built something "proper": ZFS clones, temporary mounts, sophisticated state management, careful orchestration. Multiple scripts, careful error handling, the works. 

It was a disaster.

Creating clones was easy. Destroying them? Nightmare fuel. We hit the infamous "dataset is busy" error - a known ZFS bug where kernel-level references get stuck. Nothing shows as using the dataset (lsof, fuser, all clean), but ZFS refuses to destroy it. The only fix? Reboot the entire system. This isn't some edge case - it's documented across years of OpenZFS issues (#1810, #10185, #12881, #14269) and happens regularly in production. Proxmox users report it "every 3-4 weeks."

Our clones broke the backup pipeline too. Syncoid couldn't do incremental transfers because clones held references to intermediate snapshots. We had 26+ test clones all stacked on the same mountpoint, creating a dependency nightmare that standard tools couldn't untangle. One attempt to fix it by masking ZFS services before reboot left the system unbootable - no SSH, no middleware, console recovery required. (For the gory details and recovery scripts, see [zfs-q](https://github.com/vm-wylbur/zfs-q).)

Eventually we came back to `.zfs/snapshot/` and figured out the trick: enumerate datasets first, find their snapshots individually, then parallelize across them. The large `home` dataset gets special treatment - split by subdirectory for better parallelization.

The "sophisticated" solution that didn't work: 500+ lines of code, broken backups, and mandatory reboots.
The "dumb" solution that actually works: read snapshots directly, no clones, no kernel bugs, done.

Sometimes the obvious solution needs a non-obvious implementation.

## Architecture

The pipeline is dead simple, which is why it works:

```
zfs-fd (orchestrator)
  ├── zfs-fd-capture: parallel fdfind + stat on .zfs/snapshot paths
  ├── zfs-fd-process: awk aggregation by directory depth
  └── zfs-fd-postprocess: python to generate JSON summary
```

**Key decisions that matter**:

1. **ASCII 0x1C as field separator**: Because filesystems are chaos and paths contain everything except ASCII control characters. Well, usually.

2. **Dataset-aware enumeration**: The trick that makes this work - enumerate ZFS datasets first (`backup/`, `backup/home`, `backup/zsd`), then find each one's snapshot independently. This handles the mixed files-and-datasets structure that initially confused us.

3. **Smart parallelization**: Work units are dataset-based, but huge datasets (home) get subdivided by top-level directory. This balances the work across parallel workers instead of having one worker stuck on 10M files while others sit idle.

4. **Direct snapshot reads**: No clones, no mounts, just reading from `.zfs/snapshot/<name>/`. Once we figured out the per-dataset approach, this became feasible.

5. **Streaming aggregation**: Don't load 10 million paths into memory. Stream through awk, aggregate as we go.

## Usage

### Installation

```bash
# You probably already have these, but just in case:
sudo apt install fd-find gawk python3 xz-utils

# Clone the repo
git clone <wherever-this-lives>
cd zfs-fd

# Make sure scripts are executable
chmod +x zfs-fd*
```

### Basic Usage

```bash
# Run with a unique identifier (date, purpose, whatever)
sudo ./zfs-fd backup-verification-2025-01-11

# Or if you need to customize:
sudo ./zfs-fd-capture \
  --zpool-root deep_chll/backup \
  --output /tmp/my-manifest.tsv \
  --run-id test-run-42 \
  --jobs 8 \
  --snapshot-latest
```

### Output Files

Everything lands in `/var/lib/zfs-fd/`:

- `filelist-{RUN_ID}.tsv.xz`: Compressed manifest of every file
- `topdirs-{RUN_ID}.json`: Aggregated summary by directory

The TSV includes metadata header with timestamps and runtime info:
```
# RUN_ID: 2025-08-08T12:00:06-07:00
# START_TIME: 2025-08-08T13:09:44-07:00
# ZPOOL_ROOT: deep_chll/backup
# SNAPSHOT_SELECTOR: latest
# JOBS: 4
# FORMAT: dataset<FS>size<FS>mtime<FS>fullpath (FS=ASCII 0x1C)
dataset^size^mtime^fullpath
deep_chll/backup/home^2317^1753137350^/tmp/backup-home-mount/.zfs/snapshot/syncoid_nas_to_chll_scott_2025-08-06:15:06:19-GMT-07:00/aboxer/.python_history
[... 13.6M more lines ...]
# FINISH_TIME: 2025-08-08T13:10:55-07:00
```

The JSON gives you the big picture:
```json
{
  "directories": {
    "home/user": {
      "total_size": 1234567890,
      "file_count": 42000
    },
    ...
  },
  "summary": {
    "total_files": 9876543,
    "total_directories": 1234,
    "total_bytes": 12345678901234
  }
}
```

### Options

`zfs-fd-capture` (the workhorse) supports:

- `--snapshot-latest`: Use the most recent snapshot (default)
- `--snapshot-pattern REGEX`: Match specific snapshot names
- `--jobs N`: Parallel workers (default: 4, more isn't always faster due to I/O)
- `--zpool-root PATH`: Your ZFS pool root (must end with 'backup')

## Performance & Scaling

**Real-world numbers from production** (13.6M files, 6TB - a substantial small-business dataset):
- 13,607,539 files: **71 seconds** (START_TIME: 2025-08-08T13:09:44, FINISH_TIME: 2025-08-08T13:10:55)
- Rate: ~190,000 files/second sustained
- XZ compression: adds 5-10 minutes but achieves 10:1 compression

The secret sauce? Two massive optimizations:
1. **find → fdfind**: Dropped us from 90 minutes to 25 minutes (3.6x speedup)
2. **ZFS special vdev on NVMe**: Dropped us from 25 minutes to 71 seconds (21x speedup)

Yes, I hate ZFS for its clone bugs, but credit where it's due - putting metadata on NVMe via special vdev is transformative. We went from an hour and a half to just over a minute. That's a 76x improvement overall.

This isn't your typical home backup - it's a real business-scale dataset. For comparison of different approaches, see [A Four-Way Race: Finding the Right Tool for a Big Data Job](https://wylbursinnergeek.net/2025/07/22/a-four-way-race-finding-the-right-tool-for-a-big-data-job/).

**Bottlenecks**:
- Disk I/O for metadata reads (test it though - might surprise you)
- Aggregation gets memory-hungry above 50M files
- XZ compression time is non-trivial for large datasets

**Scaling tips**:
- More parallel jobs help up to your disk's IOPS limit (usually 4-8)
- Split large runs by dataset if needed
- Consider sampling for exploratory analysis
- Profile first, assume never

## Output Interpretation

When comparing snapshots to live filesystems, expect these patterns:

- **Size mismatches with same mtime**: Package reinstalls, especially `google-cloud-sdk` and friends
- **1980 timestamps**: mtime=0 artifacts, not corruption
- **Missing from snapshot**: Files created after snapshot (duh)
- **Missing from live**: Deleted files, or you're looking at the wrong dataset

## Lessons Learned

1. **Trust your first instinct, then push through the confusion**: We started with `.zfs/snapshot/` access, got confused by the dataset structure, abandoned it for clones, then came back when clones were too slow. The right solution was our first instinct, but it needed more understanding of ZFS dataset organization. Don't give up on the simple approach just because the first attempt doesn't work.

2. **Find your actual limits**: Don't assume you're I/O bound - test it! We assumed parallel processing wouldn't help, but it turns out 4-8 workers made a huge difference. Your bottleneck might not be where you think.

3. **Modern tools matter**: Traditional `find` is painfully slow. `fdfind` is literally 10-100x faster for this workload. The unix philosophy holds (small tools, composed well) but that doesn't mean we're stuck with 1970s implementations. Also: `awk`, `xargs`, and `stat` are workhorses that handle millions of records without burping.

4. **Compression is magic but costs time**: Yes, 10:1 compression is amazing for storage and transfer. But xz compression takes real wall-clock time - factor that into your pipeline. Sometimes you want the data now, not compressed later.

## License
(c) HRDAG, 2025, GPL-2 or newer
Because good tools should be free, and filesystem enumeration shouldn't be rocket science.

## Authors

PB, Claude, and a brief appearance by Gemini (who contributed the JSON postprocessor before we decided Python was fine, actually).
