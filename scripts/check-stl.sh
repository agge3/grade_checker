#!/usr/bin/env bash

# Exits with error if CXX STL found. Exits without error is CXX STL not found.

# Search strings.
stl=("using namespace std", "std::vector", "std::list")

cpp=$(./find_cpp.sh)
hpp=$(./find_hpp.sh)
fhs=() # xxx join those arrays

for fh in "${fhs[@]}"
do
	# xxx pwd this and echo it out to stdout, so it can be logged
	for search in "${stl[@]}"
	do
	    if grep -q "$search" "$fh"; then
			exit 1
	    fi
	done
done

exit 0
