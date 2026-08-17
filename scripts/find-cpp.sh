#!/usr/bin/env bash

# Cross-platform script to find `.cpp` files
# Works on both Linux (GNU find) and macOS (BSD find)
# EXAMPLE: To search for `class HashTable`, run as `./find-cpp.sh hash table`.

# Optionally specified directory to search in.
if [[ -d $1 ]]; then
	search_dir=${1:-.}
	shift
else
	search_dir='.'
fi

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
	# macOS (BSD find)
	OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
	# Linux (GNU find)
	OS="linux"
else
	# Fallback to generic approach
	OS="generic"
fi

# Build array of file patterns
declare -a patterns
extensions=("cpp" "cxx" "cc")

if [[ $# -gt 0 ]]; then
	# If arguments provided, build class-specific patterns
	# e.g., for "hash table", find: hash_table.cpp, hash-table.cpp, hashtable.cpp, etc.
	class_pattern=""
	for arg in "$@"; do
		if [[ -z "$class_pattern" ]]; then
			class_pattern="$arg"
		else
			class_pattern="${class_pattern}[_-]*$arg"
		fi
	done
	
	for ext in "${extensions[@]}"; do
		patterns+=("*${class_pattern}.${ext}")
		patterns+=("*${class_pattern^^}.${ext}")
		patterns+=("*${class_pattern,,}.${ext}")
	done
else
	# If no arguments, find all .cpp/.cxx/.cc files
	for ext in "${extensions[@]}"; do
		patterns+=("*.${ext}")
	done
fi

# Execute find with appropriate syntax for the OS
if [[ "$OS" == "macos" ]]; then
	# BSD find: combine patterns with -o (OR)
	find_args=("-type" "f" "(" )
	for i in "${!patterns[@]}"; do
		find_args+=("-iname" "${patterns[$i]}")
		if [[ $((i + 1)) -lt ${#patterns[@]} ]]; then
			find_args+=("-o")
		fi
	done
	find_args+=(")")
	
	find "$search_dir" "${find_args[@]}" | sed "s|^${search_dir}/||" | sed "s|^${search_dir}||"
else
	# Linux (GNU find): use regex or multiple -iname with OR
	find_args=("-type" "f" "(" )
	for i in "${!patterns[@]}"; do
		find_args+=("-iname" "${patterns[$i]}")
		if [[ $((i + 1)) -lt ${#patterns[@]} ]]; then
			find_args+=("-o")
		fi
	done
	find_args+=(")")
	
	find "$search_dir" "${find_args[@]}" | sed "s|^${search_dir}/||" | sed "s|^${search_dir}||"
fi

