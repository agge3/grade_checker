#!/usr/bin/env bash

# Default usage is to search for all `.hpp` files. Provide optional arguments to
# search for class-specific `.hpp` files.
# EXAMPLE: To search for `class HashTable`, run as `./find_hpp.sh hash table`.

# If there's arguments, construct the regex pattern to search for `.hpp` files
# for the class, and their variations.
# GOAL: ".*hash[ _-]?table\.(hpp|h|hh)"
re=".*"
for (( i = 1; i < $#; i++ )); do
    re="${re}${!i}[ _-]?"
done
re="${re}${!#}\.(hpp|h|hh)"

#echo "Constructed regex pattern: $re"

# Prints results to stdout.
find . -type f -regextype posix-extended -iregex "$re" | sed 's|^\./||'
