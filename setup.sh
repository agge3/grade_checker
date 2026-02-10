#!/usr/bin/env bash

DIRS=(
	"project_fhs"
	"repos"
)

for d in "${DIRS[@]}"; do
	if [[ ! -d "$d" ]]; then
		mkdir -vp "$d"
	fi
	echo "directory already exists: $d"
done
