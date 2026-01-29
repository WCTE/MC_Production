#!/bin/bash

# ==============================================================================
# Setup script for WCTE MC Production
# 
# Usage: source setup.sh <sif_file> [sandbox_dir] [--build]
# ==============================================================================

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script must be sourced, not executed."
    echo "Usage: source setup.sh <sif_file> [sandbox_dir] [--build] (or . setup.sh)"
    exit 1
fi

if [ $# -lt 1 ]; then
    echo "Usage: source setup.sh <sif_file> [sandbox_dir] [--build]"
    return 1
fi

# Path to the Singularity Image File (.sif)
export SOFTWARE_SIF_FILE=$(readlink -f "$1")
shift

SANDBOX_ARG=""
DO_BUILD=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            DO_BUILD=true
            shift
            ;;
        *)
            SANDBOX_ARG="$1"
            shift
            ;;
    esac
done

if [ -n "$SANDBOX_ARG" ]; then
    export SOFTWARE_SANDBOX_DIR=$(readlink -f "$SANDBOX_ARG")
else
    unset SOFTWARE_SANDBOX_DIR
fi

# ------------------------------------------------------------------------------
# Build Sandbox (Optional)
# ------------------------------------------------------------------------------

if [ "$DO_BUILD" = true ]; then
    if [ -z "$SOFTWARE_SANDBOX_DIR" ]; then
        echo "Error: Sandbox directory must be specified with --build"
        return 1
    fi
    echo "Building sandbox at $SOFTWARE_SANDBOX_DIR from $SOFTWARE_SIF_FILE..."
    singularity build --sandbox "$SOFTWARE_SANDBOX_DIR" "$SOFTWARE_SIF_FILE"
fi

echo "Environment configured:"
echo "  SOFTWARE_SIF_FILE=$SOFTWARE_SIF_FILE"
if [ -n "$SOFTWARE_SANDBOX_DIR" ]; then
    echo "  SOFTWARE_SANDBOX_DIR=$SOFTWARE_SANDBOX_DIR"
fi
