#!/usr/bin/env bash

# Exits with error if CXX STL found. Exits without error if CXX STL not found.

# Search strings.
static=("static")

cpp=$(./find_cpp.sh)
hpp=$(./find_hpp.sh)
fhs=() # xxx join those arrays

for fh in "${fhs[@]}"
do
	for search in "${stl[@]}"
	do
	    if grep -q "$search" "$fh"; then
			exit 1
	    fi
	done
done

exit 0
