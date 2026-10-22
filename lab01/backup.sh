#!/bin/bash
#
# backup.sh - create a tar.gz backup of a directory
#
# Usage: backup.sh SOURCE_DIR [DEST_DIR]
#   SOURCE_DIR  directory to back up (required)
#   DEST_DIR    where to put the archive (default: /backup)
#
# Exit codes: 0 - archive created (or help shown), 1 - error

set -euo pipefail

# Print usage information
usage() {
    echo "Usage: backup.sh SOURCE_DIR [DEST_DIR]"
    echo "  SOURCE_DIR  directory to back up (required)"
    echo "  DEST_DIR    destination directory (default: /backup)"
    echo "  -h, --help  show this help and exit"
}

# Print an error message to stderr and exit with code 1
die() {
    echo "backup.sh: error: $1" >&2
    exit 1
}

# Make sure the source exists and the destination exists and is writable
check_dirs() {
    local src_dir="$1"
    local dest_dir="$2"

    [ -d "$src_dir" ] || die "source directory '$src_dir' does not exist"
    [ -d "$dest_dir" ] || die "destination directory '$dest_dir' does not exist (create it first)"
    [ -w "$dest_dir" ] || die "destination directory '$dest_dir' is not writable"
}

# Pack the source directory into a timestamped tar.gz archive
make_backup() {
    local src_dir="$1"
    local dest_dir="$2"
    local src_parent
    local src_name
    local stamp
    local archive_path

    src_parent=$(dirname "$src_dir")
    src_name=$(basename "$src_dir")
    stamp=$(date +%Y%m%d_%H%M%S)
    archive_path="${dest_dir}/backup_${src_name}_${stamp}.tar.gz"

    tar -czf "$archive_path" -C "$src_parent" "$src_name" || die "failed to create archive '$archive_path'"
    echo "backup.sh: archive created: $archive_path"
}

# Entry point
main() {
    local src_dir="${1:-}"
    local dest_dir="${2:-/backup}"

    case "$src_dir" in
        -h|--help)
            usage
            exit 0
            ;;
        "")
            usage >&2
            die "source directory is required"
            ;;
    esac

    # strip a trailing slash so basename/dirname work as expected
    if [ "$src_dir" != "/" ]; then
        src_dir="${src_dir%/}"
    fi
    if [ "$dest_dir" != "/" ]; then
        dest_dir="${dest_dir%/}"
    fi

    check_dirs "$src_dir" "$dest_dir"
    make_backup "$src_dir" "$dest_dir"
}

main "$@"
