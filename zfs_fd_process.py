#!/usr/bin/env python3
# Author: PB and Gemini
# Date: 2025-07-23
# License: (c) HRDAG, 2025, GPL-2 or newer
#
# ------
# zfs_fd_process.py

"""
ZFS-FD filelist processor: Convert raw file metadata into directory size analysis.
"""

import json
import sys
import os
import argparse
import logging
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
import multiprocessing as mp
from functools import partial

@dataclass
class DirectoryStats:
    total_size: int = 0
    file_count: int = 0
    files: list = None # Disabled for performance
    subdirs: dict = None # Disabled for performance

def read_in_chunks(file_handle, chunk_size):
    while True:
        lines = [file_handle.readline() for _ in range(chunk_size)]
        lines = [line for line in lines if line]
        if not lines:
            break
        yield lines

def process_chunk_worker(lines, base_path, depth):
    """Worker function that uses only pickle-safe types."""
    # Use a regular dict to avoid lambda serialization issues
    local_aggregates = {}
    base_path_obj = Path(base_path)

    for line in lines:
        try:
            parts = line.strip().split(None, 2)
            if len(parts) < 2:
                continue

            full_path = parts[-1]
            if not full_path.startswith('/'):
                continue

            size = int(parts[0])
            full_path_obj = Path(full_path)

            if not full_path_obj.is_relative_to(base_path_obj):
                continue

            relative_path = full_path_obj.relative_to(base_path_obj)
            path_parts = relative_path.parts

            for d in range(1, len(path_parts) + 1):
                if d > depth:
                    break
                dir_key = '/'.join(path_parts[:d])
                
                # Manual defaultdict logic
                if dir_key not in local_aggregates:
                    local_aggregates[dir_key] = {'total_size': 0, 'file_count': 0}
                
                local_aggregates[dir_key]['total_size'] += size
                local_aggregates[dir_key]['file_count'] += 1

        except (ValueError, IndexError):
            continue

    return local_aggregates

def process_filelist(input_path: str, base_path: str, depth: int = 3) -> dict:
    logging.info(f"Processing {input_path} with parallel engine (V3 Architecture).")
    num_processes = mp.cpu_count()
    chunk_size = 200000
    merged_simple_aggregates = defaultdict(lambda: {'total_size': 0, 'file_count': 0})

    with open(input_path, 'r', encoding='utf-8', errors='surrogateescape') as f:
        with mp.Pool(processes=num_processes) as pool:
            process_func = partial(process_chunk_worker, base_path=base_path, depth=depth)
            results = pool.imap_unordered(process_func, read_in_chunks(f, chunk_size))

            for worker_result in results:
                for path, stats in worker_result.items():
                    merged_simple_aggregates[path]['total_size'] += stats['total_size']
                    merged_simple_aggregates[path]['file_count'] += stats['file_count']

    # The final dict will hold the rich DirectoryStats objects
    final_aggregates = defaultdict(DirectoryStats)
    for path, stats in merged_simple_aggregates.items():
        final_aggregates[path] = DirectoryStats(total_size=stats['total_size'], file_count=stats['file_count'])

    total_files = sum(s.file_count for s in final_aggregates.values())
    logging.info(f"Processed {total_files:,} file entries into {len(final_aggregates):,} directories.")

    result = {
        'directories': {p: {"total_size": s.total_size, "file_count": s.file_count, "files": [], "subdirs": {}} for p, s in final_aggregates.items()},
        'summary': {
            'total_files': total_files,
            'total_directories': len(final_aggregates),
            'total_bytes': sum(s.total_size for s in final_aggregates.values())
        }
    }
    return result

def setup_logging(console_level: str = "INFO", logfile: str = None):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%H:%M:%S')

def main():
    parser = argparse.ArgumentParser(description="Process ZFS-FD filelist into directory size analysis")
    parser.add_argument('--input', required=True, help='Input filelist.txt path')
    parser.add_argument('--output', required=True, help='Output JSON file path')
    parser.add_argument('--base-path', required=True)
    parser.add_argument('--depth', type=int, default=3)
    parser.add_argument('--logfile', help='Optional log file path')
    args = parser.parse_args()
    
    setup_logging(console_level="INFO", logfile=args.logfile)
    
    logging.info(f"Starting zfs_fd_process.py")
    result = process_filelist(args.input, args.base_path, args.depth)
    
    with open(args.output, 'w') as f:
        json.dump(result, f, indent=2)
    logging.info(f"Output written to {args.output}")

if __name__ == "__main__":
    main()
