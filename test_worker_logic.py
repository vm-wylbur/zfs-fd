import pytest
from zfs_fd_process import process_chunk, DirectoryStats
from collections import defaultdict

TRICKY_LINES_FILE = "tests/fixtures/tricky_lines.txt"
BASE_PATH = "/storage/tmp/zfs-fd-analysis/"

def test_process_chunk_logic():
    """Tests the worker function against a known set of tricky lines."""
    with open(TRICKY_LINES_FILE, 'r') as f:
        lines = f.readlines()

    result = process_chunk(
        lines=lines,
        base_path=BASE_PATH,
        depth=3
    )

    # --- CORRECTED Assertions ---
    # The script should process ALL FOUR lines that have a size and a path.
    # The line with only ".pdf" is the only one that should be skipped.

    # 1. Check the top-level directory aggregation
    # The total size should be the sum of all 4 valid lines.
    assert result["home"].total_size == 1534
    assert result["home"].file_count == 4

    # 2. Check a mid-level directory
    assert result["home/tarak"].total_size == 1534
    assert result["home/tarak"].file_count == 4
    
    # 3. Check the deepest directory in our test data
    assert result["home/tarak/git"].total_size == 1534
    assert result["home/tarak/git"].file_count == 4

    # 4. Check that no other unexpected directories were created
    assert len(result) == 3

