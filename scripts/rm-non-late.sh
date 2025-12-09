#!/usr/bin/env bash

# Collect all *LATE* directories (depth 1)
mapfile -t DIRS < <(find . -mindepth 1 -maxdepth 1 -name "*LATE*")

# Collect all directories (depth 1)
mapfile -t RM_DIRS < <(find . -mindepth 1 -maxdepth 1)

# Remove non-LATE directories
for r in "${RM_DIRS[@]}"; do
	if [[ $(realpath "$r") == $(realpath "$0") ]]; then
		continue
	fi
	flag=false
	for d in "${DIRS[@]}"; do
		if [[ "$r" == "$d" ]]; then
			flag=true
			break
		fi
	done

	if [[ $flag == false ]]; then
		rm -rvf -- "$r"
	fi
done
