#!/usr/bin/env bash

# Default usage is to search for all `.cpp` files. Provide optional arguments to
# search for class-specific `.cpp` files.
# EXAMPLE: To search for `class HashTable`, run as `./find_cpp.sh hash table`.

# Optionally specified directory to search in.
if [[ -d $1 ]]; then
	search_dir=${1:-.}
	# Remove the directory argument, so we can proceed assuming arguments start
	# at `$1`.
	shift
else
	search_dir='.'
fi

# If there's arguments, construct the regex pattern to search for `.cpp` files
# for the class, and their variations.
# GOAL: ".*hash[ _-]?table\.cpp|h|hh)"
re=".*"
for (( i = 1; i < $#; i++ )); do
    re="${re}${!i}[ _-]?"
done
re="${re}${!#}\.cpp|cxx|cc)"

#echo "Constructed regex pattern: $re"

# Prints results to stdout.
find ${search_dir} -type f -regextype posix-extended -iregex "$re" | sed "s|^${search_dir}/||"
