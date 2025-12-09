#!/usr/bin/env bash

# list of files/directories to cloc
INCLUDE=(
	"cloc-repo.sh"
	"config.py"
	"core"
	"dist-file.sh"
	".env"
	".git"
	".gitignore"
	"grade_checker.py"
	"__init__.py"
	"main.ps1"
	"main.py"
	"milestones"
	"README.md"
	"reconstruct.sh"
	"requirements.txt"
	"scripts"
	"tests"
	"tools"
	"trim-repo.sh"
	"unit-tests.py"
)

mapfile -t DIRS < <(find . -mindepth 1 -maxdepth 1 -printf "%P\n")
EXCLUDE=($(printf "%s\n" "${DIRS[@]}" | grep -Fxv -f <(printf "%s\n" "${INCLUDE[@]}")))

# flatten into comma-separated list
printf -v EXCLUDE_LIST "%s," "${EXCLUDE[@]}"
EXCLUDE_LIST=${EXCLUDE_LIST%,}

echo "DEBUG: EXCLUDE_LIST: $EXCLUDE_LIST"

# NOTE: --by-file to see counted files
cloc . --exclude_dir="$EXCLUDE_LIST"
