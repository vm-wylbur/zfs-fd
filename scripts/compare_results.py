import json
import sys

def compare_json_files(file1, file2):
    with open(file1, 'r') as f1:
        data1 = json.load(f1)["directories"]
    with open(file2, 'r') as f2:
        data2 = json.load(f2)["directories"]

    # Normalize keys by stripping leading slashes
    norm_data1 = {k.lstrip('/'): v for k, v in data1.items()}
    norm_data2 = {k.lstrip('/'): v for k, v in data2.items()}

    keys1 = set(norm_data1.keys())
    keys2 = set(norm_data2.keys())

    only_in_1 = keys1 - keys2
    only_in_2 = keys2 - keys1

    if only_in_1:
        print(f"--- {len(only_in_1)} paths found only in {file1} ---")
        for key in sorted(list(only_in_1)):
            print(key)

    if only_in_2:
        print(f"--- {len(only_in_2)} paths found only in {file2} ---")
        for key in sorted(list(only_in_2)):
            print(key)

    common_keys = keys1.intersection(keys2)
    size_diffs = []
    for key in common_keys:
        size1 = norm_data1[key]['total_size']
        size2 = norm_data2[key]['total_size']
        if size1 != size2:
            size_diffs.append((key, size1, size2))

    if size_diffs:
        print(f"--- Found {len(size_diffs)} paths with different total_size ---")
        for key, size1, size2 in size_diffs:
            print(f"Path: {key}")
            print(f"  Golden: {size1}")
            print(f"  Awk:    {size2}")
            print(f"  Diff:   {size1 - size2}")

    if not only_in_1 and not only_in_2 and not size_diffs:
        print("✅ Validation SUCCESS: All paths and sizes match!")

if __name__ == "__main__":
    compare_json_files(sys.argv[1], sys.argv[2])
