#!/usr/bin/env python3
"""
Deep analysis focusing on box.net files and specific patterns identified.
"""

import pandas as pd
from datetime import datetime
import numpy as np

def analyze_boxnet_patterns():
    """Analyze box.net specific patterns and other concerning issues"""
    
    print("DEEP ANALYSIS OF BOX.NET FILES AND PATTERNS")
    print("="*80)
    
    # 1. Analyze older files only in backup - are they all box.net?
    print("\n1. OLDER FILES ONLY IN BACKUP - BOX.NET FOCUS")
    try:
        backup_only = pd.read_csv('only_in_backup.csv')
        backup_only['datetime'] = pd.to_datetime(backup_only['mtime'], unit='s')
        filelist_date = datetime(2025, 7, 29, 12, 6, 2)
        backup_only['days_since_filelist'] = (backup_only['datetime'] - filelist_date).dt.total_seconds() / (24*3600)
        
        # Identify box.net files
        backup_only['is_boxnet'] = backup_only['path'].str.contains('/box.net/', na=False)
        
        # Focus on files older than filelist
        older_files = backup_only[backup_only['days_since_filelist'] <= 0]
        
        print(f"Total older files: {len(older_files):,}")
        print(f"Box.net files: {older_files['is_boxnet'].sum():,}")
        print(f"Non-box.net files: {(~older_files['is_boxnet']).sum():,}")
        print(f"Percentage box.net: {(older_files['is_boxnet'].sum() / len(older_files) * 100):.1f}%")
        
        # Show age distribution for box.net vs others
        print(f"\nAge distribution for older files:")
        print(f"Box.net files - earliest: {older_files[older_files['is_boxnet']]['datetime'].min()}")
        print(f"Box.net files - latest: {older_files[older_files['is_boxnet']]['datetime'].max()}")
        print(f"Non-box.net files - earliest: {older_files[~older_files['is_boxnet']]['datetime'].min()}")
        print(f"Non-box.net files - latest: {older_files[~older_files['is_boxnet']]['datetime'].max()}")
        
        # Sample non-box.net older files
        print(f"\nSample non-box.net older files:")
        non_boxnet_older = older_files[~older_files['is_boxnet']].head()
        for _, row in non_boxnet_older.iterrows():
            print(f"  {row['datetime']}: {row['path'][:100]}...")
        
    except FileNotFoundError:
        print("  only_in_backup.csv not found")
    
    # 2. Analyze files only in filelist by dataset/location
    print("\n2. FILES ONLY IN FILELIST - DATASET ANALYSIS")
    try:
        filelist_only = pd.read_csv('only_in_filelist.csv')
        filelist_only['datetime'] = pd.to_datetime(filelist_only['mtime'], unit='s')
        
        # Extract dataset patterns
        filelist_only['is_boxnet'] = filelist_only['path'].str.contains('/box.net/', na=False)
        filelist_only['is_home'] = filelist_only['path'].str.contains('/home/', na=False)
        filelist_only['is_zsd'] = filelist_only['path'].str.contains('/zsd/', na=False)
        
        print(f"Total files only in filelist: {len(filelist_only):,}")
        print(f"Box.net files: {filelist_only['is_boxnet'].sum():,}")
        print(f"Home files: {filelist_only['is_home'].sum():,}")
        print(f"ZSD files: {filelist_only['is_zsd'].sum():,}")
        
        # Show patterns of what's missing
        print(f"\nDataset patterns in files only in filelist:")
        filelist_only['dataset'] = filelist_only['path'].str.extract(r'(deep_chll/backup/[^/]+)')
        print(filelist_only['dataset'].value_counts())
        
    except FileNotFoundError:
        print("  only_in_filelist.csv not found")
    
    # 3. Focus on google-cloud-sdk and reinstallation patterns
    print("\n3. REINSTALLATION PATTERNS (google-cloud-sdk example)")
    try:
        size_mismatches = pd.read_csv('size_mismatches.csv')
        mtime_mismatches = pd.read_csv('mtime_mismatches.csv')
        both_mismatches = pd.read_csv('both_mismatches.csv')
        
        # Look for common reinstallation indicators
        reinstall_patterns = [
            'google-cloud-sdk',
            '/lib/python',
            '/site-packages',
            '.venv',
            '/node_modules',
            '/go/pkg',
            '/cache/',
            '.install'
        ]
        
        print(f"Size mismatches - reinstallation indicators:")
        for pattern in reinstall_patterns:
            count = size_mismatches['path'].str.contains(pattern, na=False).sum()
            if count > 0:
                print(f"  {pattern}: {count} files")
        
        # Check if files with future timestamps in filelist are reinstalled components
        if 'filelist_mtime' in mtime_mismatches.columns:
            mtime_mismatches['backup_datetime'] = pd.to_datetime(mtime_mismatches['backup_mtime'], unit='s')
            mtime_mismatches['filelist_datetime'] = pd.to_datetime(mtime_mismatches['filelist_mtime'], unit='s')
            
            # Files where filelist is newer (concerning cases)
            filelist_newer = mtime_mismatches[mtime_mismatches['filelist_datetime'] > mtime_mismatches['backup_datetime']]
            
            print(f"\nFiles where filelist is newer - pattern analysis:")
            for pattern in reinstall_patterns:
                count = filelist_newer['path'].str.contains(pattern, na=False).sum()
                if count > 0:
                    print(f"  {pattern}: {count} files")
            
            # Show specific examples with context
            print(f"\nSpecific examples of filelist newer than backup:")
            for _, row in filelist_newer.head().iterrows():
                print(f"  Path: {row['path'][:80]}...")
                print(f"    Backup: {row['backup_datetime']}")
                print(f"    Filelist: {row['filelist_datetime']}")
                print(f"    Difference: {((row['filelist_datetime'] - row['backup_datetime']).total_seconds() / (24*3600)):.1f} days")
        
    except FileNotFoundError as e:
        print(f"  Missing file: {e}")
    
    # 4. Check for timestamp parsing issues
    print("\n4. TIMESTAMP PARSING ANALYSIS")
    try:
        backup_only = pd.read_csv('only_in_backup.csv')
        backup_only['datetime'] = pd.to_datetime(backup_only['mtime'], unit='s')
        
        # Look for suspicious timestamp patterns
        print(f"Timestamp anomalies:")
        print(f"  Files with 1980 dates: {(backup_only['datetime'].dt.year == 1980).sum():,}")
        print(f"  Files with future dates: {(backup_only['datetime'] > datetime.now()).sum():,}")
        
        # Check if 1980 dates correlate with specific paths
        files_1980 = backup_only[backup_only['datetime'].dt.year == 1980]
        if len(files_1980) > 0:
            files_1980['is_boxnet'] = files_1980['path'].str.contains('/box.net/', na=False)
            print(f"  1980 files that are box.net: {files_1980['is_boxnet'].sum():,}")
            print(f"  Sample 1980 files:")
            for _, row in files_1980.head().iterrows():
                print(f"    {row['path'][:100]}...")
        
    except FileNotFoundError:
        print("  only_in_backup.csv not found")
    
    print("\n" + "="*80)
    print("CONCLUSIONS:")
    print("1. Box.net file analysis will show if timestamp issues are source-specific")
    print("2. Reinstallation patterns explain filelist > backup timestamps")
    print("3. Size mismatches with same mtime suggest filesystem metadata differences")
    print("4. 1980 timestamps indicate mtime=0 or parsing issues")

if __name__ == "__main__":
    analyze_boxnet_patterns()
