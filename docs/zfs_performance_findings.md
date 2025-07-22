#---
# **Status**: The performance findings from this analysis have been integrated into the tool's design.
#---
#---
# **Status**: The performance findings from this analysis have been integrated into the tools
# ZFS Performance Analysis: Special VDEV and RAID-Z2

## 1. Executive Summary

An investigation into the performance of a `deep_chll` ZFS pool revealed that adding a mirrored NVMe special vdev for metadata resulted in a consistent **~2x speedup** for full metadata scans (~153s vs. ~296s). The legacy HDD-only system's performance of ~296s was found to be exceptionally strong, a testament to ZFS's I/O optimization and the read performance of a RAID-Z2 vdev. The primary bottleneck in the current system is likely not raw I/O, but the architectural overhead of processing millions of file lookups.

## 2. The Initial Question

The investigation sought to quantify the performance impact of a mirrored NVMe special vdev on metadata-intensive workloads. A full filesystem scan (`fdfind`) of ~13 million files was used as the benchmark.

## 3. Methodology: The Cold Cache Test

To establish a true, worst-case baseline performance for the legacy HDD-only configuration, a carefully controlled experiment was conducted.

1.  **Snapshot Creation:** A new, temporary, and guaranteed-recursive snapshot was created on the archived `deep_chll/backup_no_vdev/nas` dataset.
    ```bash
    sudo zfs snapshot -r deep_chll/backup_no_vdev/nas@cold-cache-test-snap
    ```
2.  **Clone Creation:** A full, recursive clone of this snapshot was created using the project's `zfsrclone` script, providing a safe and isolated test environment.
    ```bash
    sudo /home/pball/projects/zfs-fd/zfsrclone --yes deep_chll/backup_no_vdev/nas@cold-cache-test-snap deep_chll/tmp/cold-cache-test
    ```
3.  **Mounting:** The new clone was fully mounted using the `zfs-fd-mount` script to ensure all nested datasets were accessible.
    ```bash
    sudo /home/pball/projects/zfs-fd/zfs-fd-mount deep_chll/tmp/cold-cache-test
    ```
4.  **Cache Elimination:** To guarantee a true "cold read" test, all system-level file caches, including the ZFS ARC, were dropped immediately before the test.
    ```bash
    sudo sh -c 'echo 3 > /proc/sys/vm/drop_caches'
    ```
5.  **The Test:** The `fdfind` command was run against the clone and its output redirected to a file to minimize measurement noise.
    ```bash
    time sudo fdfind --type f --no-ignore --hidden . /storage/tmp/cold-cache-test --exec-batch stat --format='%s %n' > filelist.tmp
    ```

## 4. Test Results

| Scenario | System Configuration | Cache State | Time (seconds) |
| :--- | :--- | :--- | :--- |
| **HDD Only** | Spinning Rust HDDs | **Cold Cache** | **296s** |
| **With Special VDEV**| NVMe Mirrored VDEV | **Cold Cache** | **153s** |

## 5. Analysis

The data reveals several key insights into the system's performance:

*   **HDD Performance:** The 296-second time to read ~13 million file metadata entries from spinning rust is exceptionally strong. This performance is attributed to ZFS's I/O coalescing and intelligent prefetching, combined with the high sequential read throughput of the 4-disk RAID-Z2 vdev.

*   **Special VDEV Performance:** The ~2x speedup is significant, especially considering the underlying workload. The primary bottleneck is no longer the raw I/O of the storage media, but the sheer CPU and software overhead required to process millions of individual file lookups.

*   **Special VDEV Contents:** The special vdev was not tested in isolation. At the time of the 153s test, it held **40.3G** of data. Approximately **~19G** of this was from pre-existing data (metadata from other datasets and a period of small file block storage). The remaining **~21G** corresponds to the metadata of the `backup_w_vdev` dataset. The test, therefore, reflects the performance of reading the target metadata from a busy, mixed-use device.

## 6. Known Unknowns and Future Work

*   **Metadata Location:** It is technically possible that a very small fraction of metadata for files in the `backup_no_vdev` test had been updated since the special vdev was added, which would place it on the NVMe. However, ZFS does not retroactively move metadata, so this quantity is assumed to be negligible.

*   **Augment `zfs-fd-capture`:** A promising next step is to modify the `zfs-fd-capture` script to record file modification times (`mtime`). This would enable a precise comparison of `fdfind` performance on files known to have been created before vs. after the special vdev was added, isolating the performance of the vdev even further.
