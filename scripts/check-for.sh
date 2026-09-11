#!/usr/bin/env bash

# Grep for each argument in the provided file (file is expected to be the first
# argument). Matching lines are printed to stdout, separated as lines.

fh="$1"
# BUG: The loop below uses `$file`, but the input variable is named `$fh`.
shift
for search in "$@"
do
    grep "$search" "$file"
done
