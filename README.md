# ZFS-FD Fast Directory Analysis Suite

A high-performance, metadata-only toolkit for ZFS directory analysis using `fd` + `stat`.

## Overview

This suite provides blazing-fast directory analysis of ZFS datasets by:
1. Creating consistent recursive snapshots with holds
2. Creating temporary clones for analysis
3. Performing metadata-only analysis with `fd` + `stat`
4. Leveraging ZFS special vdev for maximum performance
5. Cleaning up clones and snapshots when complete

**Performance**: Analyze 4.5TB in 21 seconds (200-900x faster than traditional `du`)

## Scripts

### Core Scripts

1. **`zfs-fd-snapshot`** - Create snapshot and clone
2. **`zfs-fd-mount`** - Mount cloned datasets
3. **`zfs-fd-capture`** - Fast metadata-only analysis using `fd` + `stat`
4. **`zfs-fd-cleanup`** - Clean up clones and snapshots

### Utility Scripts

5. **`zfsrclone`** - Safe ZFS cloning utility (with `--yes` flag)

## Quick Start

```bash
# Complete workflow
./zfs-fd-snapshot                    # Create snapshot and clone
./zfs-fd-mount                       # Mount cloned datasets  
./zfs-fd-capture --depth 3           # Analyze at depth 3
./zfs-fd-cleanup                     # Clean up

# Or with custom source/destination
./zfs-fd-snapshot deep_chll/backup/nas deep_chll/tmp/fd-analysis
./zfs-fd-mount deep_chll/tmp/fd-analysis
./zfs-fd-capture --depth 2 /storage/tmp/fd-analysis
./zfs-fd-cleanup --yes deep_chll/tmp/fd-analysis
```

## Output

Results are stored in `/var/lib/zfs-fd/TIMESTAMP/`:
- `summary.txt` - Top-level directory sizes
- `detailed.txt` - Analysis at specified depth
- `metadata.json` - Run metadata
- `environment.sh` - Environment variables (source this file)

Logs are stored in `/var/log/zfs-fd/TIMESTAMP.log`

## Environment Variables

Set by `zfs-fd-snapshot`, used by other scripts:
- `ZFS_FD_TIMESTAMP` - Session timestamp
- `ZFS_FD_SOURCE_SNAP` - Source snapshot (created by script)
- `ZFS_FD_CLONE_BASE` - Clone destination dataset  
- `ZFS_FD_RESULTS_DIR` - Results directory
- `ZFS_FD_LOG_FILE` - Log file path
- `ZFS_FD_DEPTH` - Default analysis depth

## Performance Innovation

**The `fd` + `stat` Approach:**
- Uses `fdfind --exec-batch stat --format='%s %n'` for metadata-only operations
- Never reads data blocks, only filesystem metadata
- Optimized for ZFS special vdev architecture
- Achieves 200-900x performance improvement over traditional `du`

**ZFS Special Vdev Benefits:**
- All metadata operations hit NVMe storage
- Reduces wear on spinning rust (RAIDZ2 drives stay idle)
- Perfect division of labor: fast storage for metadata, bulk storage for data

## Safety Features

- Creates consistent recursive snapshots with holds
- Clones for analysis (source data never modified)
- Hold verification (from `zfsrclone`)
- Comprehensive error handling
- Detailed logging
- Complete cleanup of snapshots and clones

## Performance Results

- **4.5TB dataset analysis**: 21 seconds
- **Method**: fd + stat (metadata-only)
- **Storage**: ZFS special vdev (NVMe metadata)
- **Improvement**: 200-900x faster than traditional approaches
- **Scalability**: Excellent scaling (11.6x time for 112x more data)

## Authors

- PB and Claude
- Original `zfsrclone` by Jauchi
- `fd` performance breakthrough by rust-lang community
- License: (c) HRDAG, 2025, GPL-2 or newer

## Credit Where Credit is Due

This suite's breakthrough performance is made possible by:
- **`fd`**: The fast, rust-based file finder that makes metadata-only analysis practical
- **[zfsrclone](https://gist.github.com/Jauchi/6d334233a880f0d382935632e22dd2ed)**: Safe ZFS cloning script with hold verification by Jauchi
- **ZFS Special Vdev**: NVMe storage for metadata operations
- **`stat`**: Efficient metadata extraction
- **ZFS**: Snapshot and clone capabilities for safe analysis

## Important: Cleanup and Replication

The tool creates snapshots with holds to prevent accidental deletion during analysis. These holds **must** be released to avoid blocking ZFS replication.

### Emergency Hold Cleanup

If ZFS replication is blocked by du-holder snapshots:

```bash
# Release all holds (critical for replication)
sudo ./zfs-fd cleanup --holds-only

# Check for remaining du-holder snapshots
zfs list -t snapshot | grep du-holder
```

The cleanup script now:
- Always releases holds first (highest priority)
- Searches system-wide for du-holder snapshots
- Provides clear warnings if holds cannot be released
- Can run with `--holds-only` for emergency cleanup

The main workflow (`zfs-fd run`) includes automatic cleanup with error handling to prevent holds from being left behind.
