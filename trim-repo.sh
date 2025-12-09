#!/usr/bin/env bash

milestone="milestone2"
prof="hugh"
root="."
repo="milestone-2-hash-table-"

# Gather targets (directories)
mapfile -t dirs < <(find "$root/repos/$milestone-$prof" -mindepth 1 -maxdepth 1 -type d)
echo "DEBUG: dirs: ${dirs[@]}"

for d in "${dirs[@]}"; do
	path=$(dirname "$d")
	base=$(basename "$d")
	trimmed="${base#"$repo"}"
	echo "DEBUG: trimmed: $trimmed"
	mv -v "$d" "$path/$trimmed"
done
