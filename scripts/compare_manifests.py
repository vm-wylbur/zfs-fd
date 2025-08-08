#!/usr/bin/env python3
"""
Compare two filesystem manifests with different formats and path structures.
"""

import sys
from pathlib import Path
import re
from collections import defaultdict
from datetime import datetime
import csv
import time

def analyze_path_patterns():
    """Debug function to understand all datasets by sampling across entire file"""
    print("ANALYZING ALL DATASETS BY SAMPLING ACROSS ENTIRE FILE:")
    
    # First, get total line count
    import subprocess
    result = subprocess.run(['wc', '-l', 'backup_metadata.tsv'], capture_output=True, text=True)
    total_lines = int(result.stdout.split()[0]) - 1  # subtract header
    print(f"Total lines in backup metadata: {total_lines:,}")
    
    # Sample every Nth line to get representative dataset coverage
    sample_interval = max(1, total_lines // 10000)  # Sample ~10k lines evenly distributed
    print(f"Sampling every {sample_interval}th line...")
    
    datasets = {}
    dataset_samples = {}
    
    with open("backup_metadata.tsv", 'r', encoding='utf-8', errors='replace') as f:
        f.readline()  # skip header
        for i, line in enumerate(f):
            # Only process every Nth line for representative sampling
            if i % sample_interval != 0:
                continue
                
            fields = line.strip().split('\034')
            if len(fields) >= 4:
                dataset, size, mtime, fullpath = fields
                datasets[dataset] = datasets.get(dataset, 0) + 1
                
                # Collect sample paths from each dataset
                if dataset not in dataset_samples:
                    dataset_samples[dataset] = []
                if len(dataset_samples[dataset]) < 5:
                    # Extract path
                    if '/.zfs/snapshot/' in fullpath:
                        parts = fullpath.split('/.zfs/snapshot/')
                        if len(parts) > 1:
                            after_snapshot = parts[1]
                            if '/' in after_snapshot:
                                real_path = '/' + '/'.join(after_snapshot.split('/')[1:])
                            else:
                                real_path = after_snapshot
                    else:
                        real_path = fullpath
                    
                    dataset_samples[dataset].append(real_path)
    
    print(f"\nDatasets found in sample:")
    for dataset, count in sorted(datasets.items(), key=lambda x: x[1], reverse=True):
        print(f"  {dataset}: {count:,} sampled files")
    
    print(f"\nSample paths from each dataset:")
    for dataset, samples in dataset_samples.items():
        print(f"\n  Dataset: {dataset}")
        for path in samples:
            print(f"    {path}")
            # Show proposed normalization
            normalized = dataset + path
            print(f"    -> {normalized}")
    
    # Now check what root directories exist in the samples
    print(f"\nRoot directories found in each dataset:")
    for dataset, samples in dataset_samples.items():
        roots = set()
        for path in samples:
            if path.startswith('/') and len(path.split('/')) > 1:
                root = '/' + path.split('/')[1]
                roots.add(root)
        print(f"  {dataset}: {sorted(roots)}")

def parse_backup_metadata(filepath):
    """
    Parse backup_metadata.tsv format:
    Fields separated by \034 (file separator):
    dataset, size, mtime, fullpath
    """
    files = {}
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        # Skip header
        header = f.readline().strip()
        print(f"Backup metadata header: {header}")
        
        start_time = time.time()
        processed = 0
        
        for line_num, line in enumerate(f, 2):
            line = line.strip()
            if not line:
                continue
                
            # Progress logging every 100k lines
            processed += 1
            if processed % 100000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                print(f"  Processed {processed:,} backup entries ({rate:.0f}/sec, {elapsed:.1f}s elapsed)")
                
            # Split on file separator character \034
            fields = line.split('\034')
            
            if len(fields) != 4:
                if processed <= 10:  # Only show first few warnings
                    print(f"Warning: Line {line_num} has {len(fields)} fields instead of 4")
                continue
            
            dataset, size, mtime, fullpath = fields
            
            # Extract the "real" path by removing the ZFS snapshot prefix
            snapshot_pattern = r'/\.zfs/snapshot/[^/]+/'
            match = re.search(snapshot_pattern, fullpath)
            
            if match:
                # Get everything after the snapshot path
                real_path = fullpath[match.end():]
            else:
                # If no snapshot pattern found, use the full path
                real_path = fullpath
                
            # Normalize by combining dataset + extracted path
            if not real_path.startswith('/'):
                real_path = '/' + real_path
            normalized_path = dataset + real_path
            
            files[normalized_path] = {
                'size': int(size) if size.isdigit() else 0,
                'mtime': int(mtime) if mtime.isdigit() else 0,
                'source': 'backup_metadata',
                'original_path': fullpath,
                'dataset': dataset
            }
    
    elapsed = time.time() - start_time
    print(f"  Final: {len(files):,} backup entries in {elapsed:.1f}s ({len(files)/elapsed:.0f}/sec)")
    return files

def parse_filelist(filepath):
    """
    Parse filelist.txt format:
    Space-separated: size mtime path
    """
    files = {}
    
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        start_time = time.time()
        processed = 0
        
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
                
            # Progress logging every 100k lines
            processed += 1
            if processed % 100000 == 0:
                elapsed = time.time() - start_time
                rate = processed / elapsed
                print(f"  Processed {processed:,} filelist entries ({rate:.0f}/sec, {elapsed:.1f}s elapsed)")
                
            # Split on whitespace, but path can contain spaces
            parts = line.split(' ', 2)  # Split into max 3 parts
            
            if len(parts) != 3:
                if processed <= 10:  # Only show first few warnings
                    print(f"Warning: Line {line_num} has {len(parts)} parts instead of 3")
                continue
            
            size_str, mtime_str, path = parts
            
            # Replace the storage prefix with the backup dataset prefix
            path = re.sub(r'^/storage/tmp/zfs-fd-analysis/', 'deep_chll/backup/', path)

            # Normalize the path
            normalized_path = path
            
            files[normalized_path] = {
                'size': int(size_str) if size_str.isdigit() else 0,
                'mtime': int(mtime_str) if mtime_str.isdigit() else 0,
                'source': 'filelist',
                'original_path': path
            }
    
    elapsed = time.time() - start_time
    print(f"  Final: {len(files):,} filelist entries in {elapsed:.1f}s ({len(files)/elapsed:.0f}/sec)")
    return files

def compare_manifests(backup_files, filelist_files):
    """
    Compare the two file manifests and generate a report.
    """
    print("Starting comparison phase...")
    start_time = time.time()
    
    all_paths = set(backup_files.keys()) | set(filelist_files.keys())
    total_paths = len(all_paths)
    print(f"  Comparing {total_paths:,} unique paths...")
    
    # Statistics
    stats = {
        'total_backup': len(backup_files),
        'total_filelist': len(filelist_files),
        'only_in_backup': 0,
        'only_in_filelist': 0,
        'in_both': 0,
        'size_mismatch': 0,
        'mtime_mismatch': 0,
        'both_mismatch': 0,
        'identical': 0
    }
    
    results = {
        'only_in_backup': [],
        'only_in_filelist': [],
        'size_mismatch': [],
        'mtime_mismatch': [],
        'both_mismatch': [],
        'identical': []
    }
    
    processed = 0
    for path in sorted(all_paths):
        processed += 1
        
        # Progress every 100k comparisons
        if processed % 100000 == 0:
            elapsed = time.time() - start_time
            rate = processed / elapsed
            percent = (processed / total_paths) * 100
            print(f"  Compared {processed:,}/{total_paths:,} paths ({percent:.1f}%, {rate:.0f}/sec)")
        
        backup_file = backup_files.get(path)
        filelist_file = filelist_files.get(path)
        
        if backup_file and not filelist_file:
            stats['only_in_backup'] += 1
            results['only_in_backup'].append({
                'path': path,
                'size': backup_file['size'],
                'mtime': backup_file['mtime'],
                'original_path': backup_file['original_path']
            })
        elif filelist_file and not backup_file:
            stats['only_in_filelist'] += 1
            results['only_in_filelist'].append({
                'path': path,
                'size': filelist_file['size'],
                'mtime': filelist_file['mtime'],
                'original_path': filelist_file['original_path']
            })
        elif backup_file and filelist_file:
            stats['in_both'] += 1
            
            size_match = backup_file['size'] == filelist_file['size']
            mtime_match = backup_file['mtime'] == filelist_file['mtime']
            
            if size_match and mtime_match:
                stats['identical'] += 1
                # Don't store identical files to save memory
            elif not size_match and not mtime_match:
                stats['both_mismatch'] += 1
                results['both_mismatch'].append({
                    'path': path,
                    'backup_size': backup_file['size'],
                    'filelist_size': filelist_file['size'],
                    'backup_mtime': backup_file['mtime'],
                    'filelist_mtime': filelist_file['mtime'],
                    'backup_original': backup_file['original_path'],
                    'filelist_original': filelist_file['original_path']
                })
            elif not size_match:
                stats['size_mismatch'] += 1
                results['size_mismatch'].append({
                    'path': path,
                    'backup_size': backup_file['size'],
                    'filelist_size': filelist_file['size'],
                    'mtime': backup_file['mtime'],
                    'backup_original': backup_file['original_path'],
                    'filelist_original': filelist_file['original_path']
                })
            else:  # mtime mismatch only
                stats['mtime_mismatch'] += 1
                results['mtime_mismatch'].append({
                    'path': path,
                    'size': backup_file['size'],
                    'backup_mtime': backup_file['mtime'],
                    'filelist_mtime': filelist_file['mtime'],
                    'backup_original': backup_file['original_path'],
                    'filelist_original': filelist_file['original_path']
                })
    
    elapsed = time.time() - start_time
    print(f"  Comparison complete: {processed:,} paths in {elapsed:.1f}s ({processed/elapsed:.0f}/sec)")
    
    return stats, results

def print_report(stats, results):
    """
    Print a comprehensive comparison report.
    """
    print("\n" + "="*80)
    print("FILESYSTEM MANIFEST COMPARISON REPORT")
    print("="*80)
    
    print(f"\nTOTAL FILES:")
    print(f"  Backup metadata:  {stats['total_backup']:,}")
    print(f"  Filelist:         {stats['total_filelist']:,}")
    
    print(f"\nCOMPARISON RESULTS:")
    print(f"  Only in backup:      {stats['only_in_backup']:,}")
    print(f"  Only in filelist:    {stats['only_in_filelist']:,}")
    print(f"  Present in both:     {stats['in_both']:,}")
    
    print(f"\nFILES PRESENT IN BOTH:")
    print(f"  Identical:           {stats['identical']:,}")
    print(f"  Size mismatch only:  {stats['size_mismatch']:,}")
    print(f"  Mtime mismatch only: {stats['mtime_mismatch']:,}")
    print(f"  Both mismatch:       {stats['both_mismatch']:,}")
    
    # Show some examples
    print(f"\nSAMPLE DIFFERENCES:")
    
    if results['only_in_backup']:
        print(f"\nFirst 5 files only in backup:")
        for item in results['only_in_backup'][:5]:
            print(f"  {item['path']} (size: {item['size']}, mtime: {item['mtime']})")
    
    if results['only_in_filelist']:
        print(f"\nFirst 5 files only in filelist:")
        for item in results['only_in_filelist'][:5]:
            print(f"  {item['path']} (size: {item['size']}, mtime: {item['mtime']})")
    
    if results['size_mismatch']:
        print(f"\nFirst 5 files with size mismatches:")
        for item in results['size_mismatch'][:5]:
            print(f"  {item['path']}")
            print(f"    Backup: {item['backup_size']} bytes")
            print(f"    Filelist: {item['filelist_size']} bytes")
    
    if results['both_mismatch']:
        print(f"\nFirst 5 files with both size and mtime mismatches:")
        for item in results['both_mismatch'][:5]:
            print(f"  {item['path']}")
            print(f"    Backup: {item['backup_size']} bytes, mtime {item['backup_mtime']}")
            print(f"    Filelist: {item['filelist_size']} bytes, mtime {item['filelist_mtime']}")

def save_detailed_results(results, output_dir="."):
    """
    Save detailed results to CSV files for further analysis.
    """
    print("\nSaving detailed results...")
    output_dir = Path(output_dir)
    
    # Save files only in backup
    if results['only_in_backup']:
        with open(output_dir / 'only_in_backup.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['path', 'size', 'mtime', 'original_path'])
            writer.writeheader()
            writer.writerows(results['only_in_backup'])
        print(f"Saved {len(results['only_in_backup'])} files only in backup to only_in_backup.csv")
    
    # Save files only in filelist
    if results['only_in_filelist']:
        with open(output_dir / 'only_in_filelist.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['path', 'size', 'mtime', 'original_path'])
            writer.writeheader()
            writer.writerows(results['only_in_filelist'])
        print(f"Saved {len(results['only_in_filelist'])} files only in filelist to only_in_filelist.csv")
    
    # Save size mismatches
    if results['size_mismatch']:
        with open(output_dir / 'size_mismatches.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['path', 'backup_size', 'filelist_size', 'mtime', 'backup_original', 'filelist_original'])
            writer.writeheader()
            writer.writerows(results['size_mismatch'])
        print(f"Saved {len(results['size_mismatch'])} size mismatches to size_mismatches.csv")
    
    # Save both mismatches
    if results['both_mismatch']:
        with open(output_dir / 'both_mismatches.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['path', 'backup_size', 'filelist_size', 'backup_mtime', 'filelist_mtime', 'backup_original', 'filelist_original'])
            writer.writeheader()
            writer.writerows(results['both_mismatch'])
        print(f"Saved {len(results['both_mismatch'])} files with both mismatches to both_mismatches.csv")
    
    # Save mtime-only mismatches
    if results['mtime_mismatch']:
        with open(output_dir / 'mtime_mismatches.csv', 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['path', 'size', 'backup_mtime', 'filelist_mtime', 'backup_original', 'filelist_original'])
            writer.writeheader()
            writer.writerows(results['mtime_mismatch'])
        print(f"Saved {len(results['mtime_mismatch'])} mtime mismatches to mtime_mismatches.csv")

def main():
    backup_metadata_file = "backup_metadata.tsv"
    filelist_file = "/var/lib/zfs-fd/2025-07-29T12-06-02-0700/filelist.txt"
    
    print(f"Starting filesystem manifest comparison at {datetime.now()}")
    print(f"Backup file: {backup_metadata_file}")
    print(f"Filelist file: {filelist_file}")
    # analyze_path_patterns()
    
    overall_start = time.time()
    
    print("\n" + "="*50)
    print("Phase 1: Parsing backup metadata...")
    backup_files = parse_backup_metadata(backup_metadata_file)
    
    print("\n" + "="*50)
    print("Phase 2: Parsing filelist...")
    filelist_files = parse_filelist(filelist_file)
    
    print("\n" + "="*50)
    print("Phase 3: Comparing manifests...")
    stats, results = compare_manifests(backup_files, filelist_files)
    
    print("\n" + "="*50)
    print("Phase 4: Generating report...")
    print_report(stats, results)
    
    print("\n" + "="*50)
    print("Phase 5: Saving results...")
    save_detailed_results(results)
    
    total_time = time.time() - overall_start
    print(f"\n" + "="*80)
    print(f"Analysis complete! Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")

if __name__ == "__main__":
    main()

# done
