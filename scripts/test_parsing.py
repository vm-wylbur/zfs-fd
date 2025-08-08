#!/usr/bin/env python3
import sys
from pathlib import Path
import re

def test_backup_parsing():
    """Test parsing of backup_metadata.tsv format"""
    print("Testing backup metadata parsing...")
    
    with open("sample_backup.tsv", 'r') as f:
        header = f.readline().strip()
        print(f"Header: {repr(header)}")
        
        for i, line in enumerate(f):
            if i >= 5:  # Only test first 5 data lines
                break
                
            line = line.strip()
            fields = line.split('\034')
            print(f"\nLine {i+2}:")
            print(f"  Raw: {repr(line[:100])}...")
            print(f"  Fields: {len(fields)}")
            if len(fields) >= 4:
                dataset, size, mtime, fullpath = fields[:4]
                print(f"  Dataset: {dataset}")
                print(f"  Size: {size}")
                print(f"  Mtime: {mtime}")
                print(f"  Path: {fullpath}")
                
                # Extract real path
                snapshot_pattern = r'/\.zfs/snapshot/[^/]+/'
                match = re.search(snapshot_pattern, fullpath)
                if match:
                    real_path = fullpath[match.end():]
                    normalized = Path('/' + real_path).as_posix()
                    print(f"  Normalized: {normalized}")

def test_filelist_parsing():
    """Test parsing of filelist.txt format"""
    print("\n\nTesting filelist parsing...")
    
    with open("sample_filelist.txt", 'r') as f:
        for i, line in enumerate(f):
            if i >= 5:  # Only test first 5 lines
                break
                
            line = line.strip()
            parts = line.split(' ', 2)
            print(f"\nLine {i+1}:")
            print(f"  Raw: {line}")
            print(f"  Parts: {len(parts)}")
            if len(parts) >= 3:
                size, mtime, path = parts
                print(f"  Size: {size}")
                print(f"  Mtime: {mtime}")
                print(f"  Path: {path}")
                
                # Remove prefix and normalize
                path = re.sub(r'^/storage/tmp/zfs-fd-analysis/', '/', path)
                normalized = Path(path).as_posix()
                print(f"  Normalized: {normalized}")

if __name__ == "__main__":
    test_backup_parsing()
    test_filelist_parsing()
