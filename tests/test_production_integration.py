import subprocess
import os
import json
import pytest

GOLDEN_FILE = "tests/fixtures/golden_output.json"
INPUT_FILE = os.path.expanduser("~/tmp/filelist.txt")
BASE_PATH = "/storage/tmp/zfs-fd-analysis/"

def test_integration_output_matches_golden_file(tmp_path):
    output_file = tmp_path / "test_output.json"

    subprocess.run(
        [
            "python3",
            "-m",
            "zfs_fd_process",
            "--input", INPUT_FILE,
            "--output", str(output_file),
            "--base-path", BASE_PATH,
        ],
        check=True,
    )

    with open(GOLDEN_FILE, 'r') as f_golden:
        golden_data = json.load(f_golden)
    
    with open(output_file, 'r') as f_new:
        new_data = json.load(f_new)

    assert golden_data == new_data, "The output does not match the golden file."

