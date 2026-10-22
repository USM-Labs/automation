#!/bin/bash
#
# backup.sh - create a tar.gz backup of a directory
#
# Usage: backup.sh SOURCE_DIR [DEST_DIR]
#   SOURCE_DIR  directory to back up (required)
#   DEST_DIR    where to put the archive (default: /backup)

set -euo pipefail

# Print usage information
usage() {
    echo "Usage: backup.sh SOURCE_DIR [DEST_DIR]"
    echo "  SOURCE_DIR  directory to back up (required)"
    echo "  DEST_DIR    destination directory (default: /backup)"
    echo "  -h, --help  show this help and exit"
}

# Entry point
main() {
    local src_dir="${1:-}"

    case "$src_dir" in
        -h|--help)
            usage
            exit 0
            ;;
        "")
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
