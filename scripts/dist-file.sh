#!/usr/bin/env bash

milestone="milestone3"
prof="hugh"
root="."

# Gather targets (directories)
#mapfile -t targets < <(find "$root/repos/$milestone-$prof" -mindepth 1 -maxdepth 1 -type d)
targets=("svenn")
echo "DEBUG: targets: ${targets[@]}"

# Gather deploy files
mapfile -t deploy < <(find "$root/project_fhs/$milestone-$prof" -type f)
echo "DEBUG: deploy: ${deploy[@]}"

# Filter out ignore-* files
declare -a filtered
for e in "${deploy[@]}"; do
	if [[ $(basename "$e") == ignore-* ]]; then
		continue
	fi
	filtered+=("$e")
done
echo "DEBUG: filtered: ${filtered[@]}"

# Copy filtered files into each target
for ele in "${targets[@]}"; do
	for e in "${filtered[@]}"; do
		cp -d "$e" "$ele"
	done
done
