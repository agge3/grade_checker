#!/usr/bin/env bash

# Loop over all files in the current directory
for f in *; do
    # Skip if it's already a file without spaces
    [[ "$f" != *[[:space:]]* ]] && continue

    # Replace all whitespace with dashes
    newname="${f//[[:space:]]/-}"

    # Rename the file
    mv -v "$f" "$newname"
done
