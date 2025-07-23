BEGIN {
    base_path = "/storage/tmp/zfs-fd-analysis/"
    depth = 3
}
{
    # Match lines with a size and an absolute path
    if ($1 ~ /^[0-9]+$/ && $NF ~ /^\//) {
        size = $1
        # Reconstruct the full path in case it contains spaces
        full_path = $3
        for (i = 4; i <= NF; i++) {
            full_path = full_path " " $i
        }

        # Strip the base path
        if (index(full_path, base_path) == 1) {
            rel_path = substr(full_path, length(base_path) + 1)
            n = split(rel_path, parts, "/")

            # Emit a record for each directory level up to the depth
            # and up to the file itself.
            for (d = 1; d <= n && d <= depth; d++) {
                current_path = "/" parts[1]
                for (i = 2; i <= d; i++) {
                    current_path = current_path "/" parts[i]
                }
                print size, current_path
            }
        }
    }
}
