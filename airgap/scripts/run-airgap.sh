#!/bin/sh
# Run a command in a new network namespace: loopback only. Linux only; elsewhere use
# `docker run --network none`. Isolates networking, not a security sandbox.
# usage: run-airgap.sh [--probe] -- <command> [args...]
set -eu

usage() { echo "usage: run-airgap.sh [--probe] -- <command> [args...]" >&2; exit 2; }

INSIDE=0
PROBE=0
if [ "${1:-}" = "--inside" ]; then INSIDE=1; shift; fi
if [ "${1:-}" = "--probe" ]; then PROBE=1; shift; fi
[ "${1:-}" = "--" ] || usage
shift
[ "$#" -gt 0 ] || usage
DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)

if [ "$INSIDE" = 0 ]; then
  [ "$(uname -s)" = Linux ] || { echo "run-airgap.sh needs Linux; use docker run --network none" >&2; exit 2; }
  if [ "$PROBE" = 1 ]; then set -- --probe -- "$@"; else set -- -- "$@"; fi
  if command -v bwrap >/dev/null 2>&1; then
    # --dev-bind keeps the filesystem as is; only the network is new.
    exec bwrap --die-with-parent --unshare-net --dev-bind / / /bin/sh "$DIR/run-airgap.sh" --inside "$@"
  fi
  if unshare -n true 2>/dev/null; then
    exec unshare -n /bin/sh "$DIR/run-airgap.sh" --inside "$@"
  fi
  if unshare -rn true 2>/dev/null; then  # unprivileged: maps you to root inside a user namespace
    exec unshare -rn /bin/sh "$DIR/run-airgap.sh" --inside "$@"
  fi
  echo "can't create a network namespace (no bwrap, unshare -n not permitted); refusing to run unisolated" >&2
  exit 2
fi

# A new namespace from unshare starts with loopback down (bwrap brings it up itself).
command -v ip >/dev/null 2>&1 && ip link set lo up 2>/dev/null || true
if [ "$PROBE" = 1 ]; then
  python3 "$DIR/probe_network.py"  # set -e: a failed probe stops here
fi
exec "$@"
