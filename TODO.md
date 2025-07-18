# ZFS-FD TODO List

## Configuration System
- [ ] Add config file support (`.conf` format)
  - Default location: `~/.zfs-fd.conf` or `/etc/zfs-fd.conf`
  - Override hardcoded defaults in `zfs-fd-snapshot`
  - Config options: `DEFAULT_SOURCE`, `DEFAULT_CLONE_BASE`, `DEFAULT_DEPTH`, `RESULTS_BASE`

## Enhancements
- [ ] Add main wrapper script `zfs-fd` to chain all operations
- [ ] Add `--dry-run` mode for testing without actual operations
- [ ] Add progress indicators for long-running operations
- [ ] Add size filtering options (e.g., `--min-size 1G`)
- [ ] Add output format options (JSON, CSV, etc.)
- [ ] Add automatic cleanup on interrupt (trap signals)

## Error Handling
- [ ] Improve error messages with suggested fixes
- [ ] Add validation for required ZFS features
- [ ] Add disk space checks before cloning
- [ ] Add recovery options for failed operations

## Performance
- [ ] Configurable parallel job count (currently hardcoded to 8)
- [ ] Add caching for repeated analysis
- [ ] Optimize for different storage types

## Testing
- [ ] Add unit tests for individual scripts
- [ ] Add integration tests for full workflow
- [ ] Add mock/dry-run testing capabilities

## Documentation
- [ ] Add man pages for each script
- [ ] Add troubleshooting guide
- [ ] Add performance tuning guide

## Installation
- [ ] Add installation script to deploy to `/usr/local/bin/zfs-fd/`
- [ ] Add uninstall script
- [ ] Add system service integration (optional)

## Deployment
- [ ] Create git repository when scripts stabilize
- [ ] Add version management
- [ ] Add changelog

## ZFS Special vdev Metadata Migration (CRITICAL PERFORMANCE ISSUE)

**Root Cause Identified**: Current metadata performance bottleneck confirmed via web-Claude analysis.
- Dataset `deep_chll/backup/nas` created July 15, 2025 (3 days BEFORE special vdev)
- Special vdev added July 18, 2025 at 09:01:22
- All metadata stuck on slow RAIDZ2 pool (~150MB/s vs NVMe ~500MB/s potential)
- Clones inherit parent snapshot metadata locations via DVA block pointers

**Current Performance**: 
- fd enumeration: ~7 minutes on spinning rust (acceptable for now)
- Metadata reads: 500-800 IOPS from RAIDZ2 instead of 50,000+ IOPS from NVMe

**Solution**: Full send/receive migration (one-time cost, permanent fix)
```bash
# Migration command (run overnight):
sudo zfs snapshot deep_chll/backup/nas@migrate-to-special
sudo zfs send deep_chll/backup/nas@migrate-to-special | sudo zfs receive deep_chll/backup/nas-migrated

# After verification:
sudo zfs rename deep_chll/backup/nas deep_chll/backup/nas-old
sudo zfs rename deep_chll/backup/nas-migrated deep_chll/backup/nas
```

**Time Estimate**: 10-12 hours total (4.5TB at ~150MB/s read + NVMe write)

**Expected Results After Migration**:
- Directory traversal: 2-5 seconds (vs current 7 minutes)
- Metadata IOPS: 50,000+ (vs current 500-800) 
- All future clones will have metadata on NVMe automatically
- 10-100x performance improvement for all metadata operations

**Priority**: High - Schedule for overnight run when system idle

