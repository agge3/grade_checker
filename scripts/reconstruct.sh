#!/usr/bin/env bash

usage() {
	echo "Usage: $(basename "$0"): <milestoneX> [professor]" 2>&1
}

if [[ $# -ne 1 || -z "$1" ]]; then
	usage
	exit 1
fi

mapfile -t FILES < <(find . -mindepth 1 -maxdepth 1 -type f)

for f in "${FILES[@]}"; do
    base=$(basename "$f")
	if [[ "$base" == *.* ]]; then
	    ext="${base##*.}"
	    name="${base%.*}"
	else
	    ext=""
	    name="$base"
	fi
	if [[ "$ext" == "zip" || -z "$ext" ]]; then
		if [[ -z "$ext" ]]; then
			name="$name-noext"
		fi
	    echo "DEBUG: zip: $base"
	    mkdir -vp "$name"
	    unzip -o "$base" -d "$name"
		chmod -R u+rwX "$name"
		rm -rvf "$base"
    elif [[ "$ext" == cpp ]]; then
        echo "DEBUG: cpp: $base"
        mkdir -vp "$name"
        mv -v "$base" "$name"
		rm -rvf "$base"
	fi
done

root=".."
milestone="$1"
prof="${2:-hugh}"

# Gather targets (directories)
mapfile -t targets < <(find . -mindepth 1 -maxdepth 1 -type d)
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
