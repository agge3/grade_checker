#!/usr/bin/env bash

set -euo pipefail

usage() {
	echo "Usage: $(basename "$0") <sub_dir> <milestoneX> [professor]" 2>&1
}

if [[ "$(dirname "$0")" != "scripts" ]]; then
	echo "must be ran from project root as: scripts/reconstruct.sh" 2>&1
	exit 1
fi

if [[ -z "${1:-}" || -z "${2:-}" ]]; then
	usage
	exit 1
fi

SUB_DIR="$1"
MILESTONE="$2"
PROF="${3:-hugh}"

RE='^([a-zA-Z]+)_([0-9]+)_([0-9]+)_(.*)'
LATE_RE='^([a-zA-Z]+)_LATE_([0-9]+)_([0-9]+)_(.*)'

mapfile -t FILES < <(find "$SUB_DIR" -mindepth 1 -maxdepth 1 -type f)

pushd "$SUB_DIR"
for f in "${FILES[@]}"; do
	base=$(basename "$f")
	student=""
	fname=""

	# parse canvas file name
	if [[ "$base" =~ $RE ]]; then
		student="${BASH_REMATCH[1]}"
		fname="${BASH_REMATCH[4]}"
	elif [[ "$base" =~ $LATE_RE ]]; then
		student="${BASH_REMATCH[1]}-LATE"
		fname="${BASH_REMATCH[4]}"
	else
		echo "WARN: unexpected file name format: $base. skipping..."
		continue
	fi

	if [[ ! -d "$student" ]]; then
		mkdir -vp "$student"
	fi

	if [[ "$fname" == *.zip ]]; then
		echo "DEBUG: zip: $base -> $student"
		unzip -o "$base" -d "$student"
		# students may have weird permissions in their zip
		chmod -R u+rwX "$student"
		rm -rvf "$base"
	else
		echo "DEBUG: $base -> $student/$fname"
		mv -v "$base" "$student/$fname"
	fi
done
popd

# Gather targets (directories)
mapfile -t targets < <(find "$SUB_DIR" -mindepth 1 -maxdepth 1 -type d)
echo "DEBUG: targets: ${targets[*]}"

# Gather deploy files
mapfile -t deploy < <(find "project_fhs/$MILESTONE-$PROF" -type f)
echo "DEBUG: deploy: ${deploy[*]}"

# Filter out ignore-* files
declare -a filtered
for e in "${deploy[@]}"; do
	if [[ $(basename "$e") == ignore-* ]]; then
		continue
	fi
	filtered+=("$e")
done
echo "DEBUG: filtered: ${filtered[*]}"

# Copy filtered files into each target
for ele in "${targets[@]}"; do
	for e in "${filtered[@]}"; do
		cp -v "$e" "$ele"
	done
done

# replace spaces in file names
REPLACE_SPACE="scripts/replace-space.sh"
REPLACE_SPACE_BASE="$(basename "$REPLACE_SPACE")"
mapfile -t DIST < <(find "$SUB_DIR" -mindepth 1 -maxdepth 1 -type d)
for d in "${DIST[@]}"; do
	cp -v "$REPLACE_SPACE" "$d"
	pushd "$d"
	./"$REPLACE_SPACE_BASE"
	rm -rv "$REPLACE_SPACE_BASE"
	popd
done

# copy reconstructed canvas submissions to normal infra directory
INFRA_DIR="repos/$MILESTONE-$PROF"
if [[ ! -d "$INFRA_DIR" ]]; then
	mkdir -p "$INFRA_DIR"
fi

#cp -v "$SUB_DIR"/* "$INFRA_DIR"
