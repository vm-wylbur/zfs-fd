#!/usr/bin/env python3
"""
Analyze the comparison results to understand timestamp patterns and mismatches.
"""

import pandas as pd
from datetime import datetime
import numpy as np

def analyze_results():
    """Analyze the CSV results from the manifest comparison"""
    
    # Key dates for reference
    filelist_date = datetime(2025, 7, 29, 12, 6, 2)  # From the filelist path
    analysis_date = datetime.now()
    
    print("ANALYZING COMPARISON RESULTS")
    print(f"Filelist snapshot date: {filelist_date}")
    print(f"Analysis date: {analysis_date}")
    print("="*80)
    
    # Analyze files only in backup
    print("\n1. ANALYZING FILES ONLY IN BACKUP (should be newer than July 29)")
    try:
        backup_only = pd.read_csv('only_in_backup.csv')
        print(f"Total files only in backup: {len(backup_only):,}")
        
        # Convert mtime to datetime
        backup_only['datetime'] = pd.to_datetime(backup_only['mtime'], unit='s')
        backup_only['days_since_filelist'] = (backup_only['datetime'] - filelist_date).dt.total_seconds() / (24*3600)
        
        print(f"\nTimestamp analysis:")
        print(f"  Earliest: {backup_only['datetime'].min()}")
        print(f"  Latest: {backup_only['datetime'].max()}")
        print(f"  Files newer than filelist date: {(backup_only['days_since_filelist'] > 0).sum():,}")
        print(f"  Files older than filelist date: {(backup_only['days_since_filelist'] <= 0).sum():,}")
        
        # Show some examples of older files (shouldn't exist)
        older_files = backup_only[backup_only['days_since_filelist'] <= 0].head()
        if len(older_files) > 0:
            print(f"\nSample older files (concerning):")
            for _, row in older_files.iterrows():
                print(f"  {row['datetime']}: {row['path'][:100]}...")
        
        # Show distribution by days since filelist
        print(f"\nDistribution by days since filelist snapshot:")
        bins = [-1000, -30, -7, -1, 0, 1, 7, 30, 1000]
        labels = ['Very old', '30+ days old', '1-30 days old', '1-7 days old', 'Same day', '1 day new', '1-7 days new', '1+ month new']
        backup_only['age_bucket'] = pd.cut(backup_only['days_since_filelist'], bins=bins, labels=labels)
        print(backup_only['age_bucket'].value_counts())
        
    except FileNotFoundError:
        print("  only_in_backup.csv not found")
    
    # Analyze files only in filelist  
    print("\n2. ANALYZING FILES ONLY IN FILELIST (should be older or deleted)")
    try:
        filelist_only = pd.read_csv('only_in_filelist.csv')
        print(f"Total files only in filelist: {len(filelist_only):,}")
        
        filelist_only['datetime'] = pd.to_datetime(filelist_only['mtime'], unit='s')
        filelist_only['days_since_filelist'] = (filelist_only['datetime'] - filelist_date).dt.total_seconds() / (24*3600)
        
        print(f"\nTimestamp analysis:")
        print(f"  Earliest: {filelist_only['datetime'].min()}")
        print(f"  Latest: {filelist_only['datetime'].max()}")
        print(f"  Files newer than filelist date: {(filelist_only['days_since_filelist'] > 0).sum():,}")
        print(f"  Files older than filelist date: {(filelist_only['days_since_filelist'] <= 0).sum():,}")
        
    except FileNotFoundError:
        print("  only_in_filelist.csv not found")
    
    # Analyze mtime mismatches
    print("\n3. ANALYZING MTIME MISMATCHES (backup should be newer)")
    try:
        mtime_mismatches = pd.read_csv('mtime_mismatches.csv')
        print(f"Total mtime mismatches: {len(mtime_mismatches):,}")
        
        mtime_mismatches['backup_datetime'] = pd.to_datetime(mtime_mismatches['backup_mtime'], unit='s')
        mtime_mismatches['filelist_datetime'] = pd.to_datetime(mtime_mismatches['filelist_mtime'], unit='s')
        mtime_mismatches['time_diff_hours'] = (mtime_mismatches['backup_datetime'] - mtime_mismatches['filelist_datetime']).dt.total_seconds() / 3600
        
        print(f"\nTime difference analysis (positive = backup newer):")
        print(f"  Backup newer: {(mtime_mismatches['time_diff_hours'] > 0).sum():,}")
        print(f"  Filelist newer: {(mtime_mismatches['time_diff_hours'] < 0).sum():,} (concerning)")
        print(f"  Average difference: {mtime_mismatches['time_diff_hours'].mean():.1f} hours")
        print(f"  Median difference: {mtime_mismatches['time_diff_hours'].median():.1f} hours")
        
        # Show examples where filelist is newer (problematic)
        filelist_newer = mtime_mismatches[mtime_mismatches['time_diff_hours'] < 0].head()
        if len(filelist_newer) > 0:
            print(f"\nFiles where filelist is newer (concerning):")
            for _, row in filelist_newer.iterrows():
                print(f"  Backup: {row['backup_datetime']} vs Filelist: {row['filelist_datetime']}")
                print(f"    {row['path'][:100]}...")
        
    except FileNotFoundError:
        print("  mtime_mismatches.csv not found")
    
    # Analyze size mismatches
    print("\n4. ANALYZING SIZE MISMATCHES (how can size differ without mtime?)")
    try:
        size_mismatches = pd.read_csv('size_mismatches.csv')
        print(f"Total size mismatches: {len(size_mismatches):,}")
        
        size_mismatches['size_diff'] = size_mismatches['backup_size'] - size_mismatches['filelist_size']
        size_mismatches['size_ratio'] = size_mismatches['backup_size'] / size_mismatches['filelist_size']
        size_mismatches['backup_datetime'] = pd.to_datetime(size_mismatches['mtime'], unit='s')
        
        print(f"\nSize difference analysis:")
        print(f"  Backup larger: {(size_mismatches['size_diff'] > 0).sum():,}")
        print(f"  Filelist larger: {(size_mismatches['size_diff'] < 0).sum():,}")
        print(f"  Average size difference: {size_mismatches['size_diff'].mean():.0f} bytes")
        print(f"  Median size difference: {size_mismatches['size_diff'].median():.0f} bytes")
        
        print(f"\nSample size mismatches with same mtime:")
        for _, row in size_mismatches.head().iterrows():
            print(f"  {row['backup_datetime']}: {row['backup_size']} vs {row['filelist_size']} bytes")
            print(f"    {row['path'][:100]}...")
        
    except FileNotFoundError:
        print("  size_mismatches.csv not found")
    
    # Analyze both mismatches
    print("\n5. ANALYZING BOTH SIZE AND MTIME MISMATCHES")
    try:
        both_mismatches = pd.read_csv('both_mismatches.csv')
        print(f"Total files with both mismatches: {len(both_mismatches):,}")
        
        both_mismatches['backup_datetime'] = pd.to_datetime(both_mismatches['backup_mtime'], unit='s')
        both_mismatches['filelist_datetime'] = pd.to_datetime(both_mismatches['filelist_mtime'], unit='s')
        both_mismatches['time_diff_hours'] = (both_mismatches['backup_datetime'] - both_mismatches['filelist_datetime']).dt.total_seconds() / 3600
        both_mismatches['size_diff'] = both_mismatches['backup_size'] - both_mismatches['filelist_size']
        
        print(f"\nTime and size analysis:")
        print(f"  Backup newer: {(both_mismatches['time_diff_hours'] > 0).sum():,}")
        print(f"  Backup larger: {(both_mismatches['size_diff'] > 0).sum():,}")
        
    except FileNotFoundError:
        print("  both_mismatches.csv not found")
    
    print("\n" + "="*80)
    print("CONCLUSIONS:")
    print("- Files only in backup should mostly be created after July 29")
    print("- Mtime mismatches where backup is newer are expected")
    print("- Size mismatches with same mtime suggest metadata issues or file system differences")
    print("- Any case where filelist is newer than backup needs investigation")

if __name__ == "__main__":
    analyze_results()
