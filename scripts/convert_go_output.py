import json
import sys

def convert_to_json(input_file, output_file):
    directories = {}
    total_size = 0
    base_path_to_strip = "/storage/tmp/zfs-fd-analysis/"

    with open(input_file, 'r') as f_in:
        for line in f_in:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                size_str, path_with_base = parts
                size = int(size_str)
                
                # Normalize the path
                if path_with_base.startswith(base_path_to_strip):
                    path = path_with_base[len(base_path_to_strip):]
                else:
                    path = path_with_base

                directories[path] = {
                    "total_size": size,
                    "file_count": 0, # Placeholder
                    "files": [],
                    "subdirs": {}
                }
                total_size += size

    result = {
        "directories": directories,
        "summary": {
            "total_files": 0, # Placeholder
            "total_directories": len(directories),
            "total_bytes": total_size
        }
    }

    with open(output_file, 'w') as f_out:
        json.dump(result, f_out, indent=2)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 convert_go_output.py <input_file> <output_file>")
        sys.exit(1)
    
    convert_to_json(sys.argv[1], sys.argv[2])
