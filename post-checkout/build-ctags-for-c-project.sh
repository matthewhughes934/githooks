#!/bin/sh

# Rebuild 'ctags' for a C project after moving HEAD with 'git checkout'

PREV_REF="${1:-}"
NEW_REF="${2:-}"
# WAS_BRANCH_CHANGE="${3:-}" # unused

if [ "$PREV_REF" != "$NEW_REF" ]
then
    git ls-files | ctags --languages=c --recurse --c-kinds=+l -L-
fi

