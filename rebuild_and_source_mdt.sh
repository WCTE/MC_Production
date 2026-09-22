#!/bin/bash
# rebuild_and_source_mdt.sh
#
# Run from INSIDE the container, after sourcing your WCSim fork's
# this_wcsim.sh so WCSIM_BUILD_DIR is already exported. Rebuilds MDT's
# develop/wcte branch (cpp, WCRootData, and the WCTE app - appWCTESingleEvent,
# NOT compile.sh's hardcoded appHKHybridSingleEvent, see below) against that
# WCSim, then sources envMDT.sh so MDTROOT/WCRDROOT/LD_LIBRARY_PATH end up
# set in YOUR shell.
#
# MUST be sourced, not executed - the whole point is to leave those variables
# behind in your interactive shell afterwards:
#
#   source /path/to/WCSim_acraplet/build/install/bin/this_wcsim.sh
#   source /eos/home-a/acraplet/WCSim/MC_Production/rebuild_and_source_mdt.sh
#
# Building directly on EOS is fine: EOS is a normal read-write mount inside
# the container for ordinary file I/O - it's only a container-internal
# WRITABLE-SANDBOX overlay that can't bind /eos reliably here (this
# apptainer has no overlay/underlay support), and this script doesn't use
# one.

# Where your MDT checkout lives - override by exporting MDT_DIR before
# sourcing this script, e.g. MDT_DIR=/path/to/other/checkout source ...
MDT_DIR="${MDT_DIR:-/eos/user/a/acraplet/MDT}"

# Why not just `git checkout develop/wcte` here: this MDT checkout is where
# you're also actively editing source (Makefiles, WCRootData.cc, ...) -
# silently switching branches for you risks discarding uncommitted work
# (exactly what almost happened switching branches by hand earlier). Fail
# loudly instead and let you decide (commit/stash) rather than guessing.
REQUIRED_BRANCH="develop/wcte"

# guard: `./rebuild_and_source_mdt.sh` would set MDTROOT/WCRDROOT/LD_LIBRARY_PATH
# in a throwaway subshell and throw them away the moment it exits.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "rebuild_and_source_mdt.sh must be SOURCED, not executed: 'source ${BASH_SOURCE[0]}'" >&2
    exit 1
fi

if [[ -z "${WCSIM_BUILD_DIR}" ]]; then
    echo "WCSIM_BUILD_DIR is not set - source this_wcsim.sh for your WCSim install first." >&2
    return 1
fi

if [[ ! -d "$MDT_DIR" ]]; then
    echo "MDT_DIR '$MDT_DIR' does not exist - clone MDT there, or set MDT_DIR to your checkout." >&2
    return 1
fi

current_branch="$(git -C "$MDT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null)"
if [[ "$current_branch" != "$REQUIRED_BRANCH" ]]; then
    echo "MDT_DIR ($MDT_DIR) is on branch '$current_branch', not '$REQUIRED_BRANCH'." >&2
    echo "Switch it yourself first (commit/stash anything uncommitted, then" >&2
    echo "'git -C $MDT_DIR checkout $REQUIRED_BRANCH'), then re-source this script." >&2
    return 1
fi

echo "Rebuilding MDT ($REQUIRED_BRANCH) in $MDT_DIR against WCSIM_BUILD_DIR=$WCSIM_BUILD_DIR ..."

build_failed=0
(
    set -e
    # cd into MDT_DIR BEFORE sourcing envMDT.sh: that script does
    # `export MDTROOT=$(pwd)`, so if we source it from wherever this wrapper
    # itself was sourced from (e.g. MC_Production), MDTROOT ends up pointing
    # there instead of at the actual MDT checkout - which is exactly what
    # broke the previous run (wrong -I/-L paths, "cannot find -lWCRData").
    cd "$MDT_DIR"
    source ./envMDT.sh
    cd cpp                             && make clean && make all
    cd ../app/utilities/WCRootData     && make clean && make all
    # `make clean` here too: without it, stale .o's from a build against a
    # DIFFERENT toolchain (e.g. testing this same EOS checkout from outside
    # the container) look "up to date" to make and get relinked as-is,
    # producing exactly the kind of ABI-mismatched "undefined reference"
    # errors a fresh rebuild wouldn't have.
    cd ../../application               && rm -f *.o appWCTESingleEvent && make appWCTESingleEvent
) || build_failed=1

if [[ $build_failed -ne 0 ]]; then
    echo "MDT rebuild failed - not sourcing envMDT.sh." >&2
    return 1
fi

pushd "$MDT_DIR" >/dev/null
source ./envMDT.sh
rc=$?
popd >/dev/null

if [[ $rc -ne 0 ]]; then
    echo "sourcing envMDT.sh failed." >&2
    return 1
fi

echo "MDT ($REQUIRED_BRANCH) rebuilt and sourced: MDTROOT=$MDTROOT  WCRDROOT=$WCRDROOT"
echo "Built app: $MDT_DIR/app/application/appWCTESingleEvent"
