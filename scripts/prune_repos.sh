#!/usr/bin/env bash

ROOT="$(git rev-parse --show-toplevel)"
MILESTONE="$1"
PROF="${2:-hugh}"
MILESTONE_PATH="$ROOT/repos/$MILESTONE-$PROF"
GLOB=$(grep 'glob' "$ROOT/milestones/_$MILESTONE-$PROF.json" | awk -F: '{ print $NF }' | tr -d '" ,')
NUM="${MILESTONE//[^0-9]/}"
GH_UNAMES_F="$ROOT/secrets/gh_unames.txt"

declare -A GH_UNAMES_SET
while IFS= read -r line; do
	[[ "$line" == "CANVAS" ]] && continue
	GH_UNAMES_SET["$line"]=1
done <"$GH_UNAMES_F"

readarray -t REPOS < <(find "$MILESTONE_PATH" -mindepth 1 -maxdepth 1)

for repo in "${REPOS[@]}"; do
	re="milestone-$NUM-$GLOB-"
	basename=$(basename "$repo")
	gh_uname="${basename#"$re"}"
	if [[ ! -v GH_UNAMES_SET["$gh_uname"] ]]; then
		rm -rvf "$repo"
	fi
done
