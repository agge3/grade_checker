#!/usr/bin/env bash

# Optionally specified directory to search in.
if [[ -d $1 ]]; then
	search_dir=${1:-.}
	# Remove the directory argument, so we can proceed assuming arguments start
	# at `$1`.
	shift
else
	search_dir='.'
fi

copy_project_fhs()
{
	source_dir=$1
	if [ -d "$source_dir" ] && [ "$(ls -A "$source_dir")" ]; then
        find . -mindepth 1 -maxdepth 1 -type d ! -name "$(basename "$source_dir")" -exec cp -r "$source_dir/"* {} \;
    else
        echo "Error: Source directory '$source_dir' is empty or does not exist."
    fi
}

project_fhs="project_fhs"

copy_project_fhs ${project_fhs}

cpp_fhs=(
	'doubly linked list'
	'generate output'
)

methods=(
	'isEmpty'
	'insertAtHead'
	'insertAtTail'
	'remove'
	'removeHeaderNode'
	'removeTailNode'
	'moveNodeToHead'
	'moveNodeToTail'
	'clear'
	'printList'
	'reversePrintList'
)

declare -a all_fhs
for fh in ${cpp_fhs[@]}; do
	all_fhs+=($(./find-cpp.sh ${search_dir} ${fh}))
done

print_header()
{
	local msg=$1
	local width=80

  	# Subtract 2 for spaces around the message.
	local pad=$(( (width - ${#msg} - 2) / 2 ))

    # Print the top border line.
    printf '%*s\n' "$width" | tr ' ' '#'

    # Print the centered header line.
    printf '%.*s %s %.*s\n' \
        "$pad" \
        "################################################################" \
        "$msg" "$pad" \
        "################################################################"

    # Print the bottom border line.
    printf '%*s\n' "$width" | tr ' ' '#'
}

fmt_line()
{
	local msg=$1
	local width=80

  	# Subtract 2 for spaces around the message.
	local pad=$(( (width - ${#msg} - 2) / 2 ))

    # Print the centered header line.
    printf '%.*s %s %.*s\n' \
        "$pad" \
        "################################################################" \
        "$msg" "$pad" \
        "################################################################"
}

print_header "BEGIN GRADING"
printf "\n"
print-git-log()
{
	w=80
	cd "${search_dir}"
	git log -n 3 --pretty=format:"%h %an %ad %s"
	printf "\n"
	fmt_line "NOT FOUND!"
	printf '%*s\n' "$w" | tr ' ' '#'
	cd -
}
printf "\n"

#if [[ "${search_dir}" =~ list-(.*) ]]; then
#	username="${BASH_REMATCH[1]}"
#	print_header "GITHUB USERNAME: ${username}"
#else
#	echo "XXX GitHub username not found!"
#fi

#print-git-log
#printf "\n"

for fh in ${all_fhs[@]}; do
	print_header "${fh} HEADER"
	sed -n '/\/\*\*/,/\*\//p' "${fh}"

	print_header "${fh} METHOD CHECK BEGIN"
	for fn in ${methods[@]}; do
		if ! grep -q ${fn} "${fh}"; then
			echo "${fn} missing!"
		fi
	done
	print_header "${fh} METHOD CHECK END"
done
printf "\n"

#print_header "GTEST CHECK"
#printf "\n"
#if grep -q "#include <gtest/gtest.h>" "milestone1.cpp" && \
#	grep -q "EXPECT_" "/milestone1.cpp"; then
#	print_header "FOUND GTEST"
#else
#	print_header "NO GTEST"
#fi
#printf "\n"

build()
{
	rm -rf "build"
	mkdir -p "build"
	cd "build"
	cmake ..
	make all
	./Milestone_1
	cd -
}

print_header "BUILD START"
build
print_header "BUILD END"
printf "\n"

test_out=(
	"List after testCase5:
88 80 10 10000 50 
Reverse List after testCase5:
50 10000 10 80 88"
	
	"List after testCase4:
100 1000 70 10 40 
Reverse List after testCase4:
40 10 70 1000 100"
	
	"List after testCase3:
1000 180 80 40 
Reverse List after testCase3:
40 80 180 1000 "
	
	"List after testCase2:
1000 80 50 40 
Reverse List after testCase2:
40 50 80 1000"
	
	"List after testCase1:
10 20 30 40 50 60 70 80 90 100 
Reverse List after testCase1:
100 90 80 70 60 50 40 30 20 10"
)

print_header "OUTPUT CHECK START"
for out in "${test_out[@]}"; do
    # Convert the multi-line string into a single line.
    search_str=$(echo "$out" | tr '\n' ' ')

    # Convert the file content into a single line too.
    file_content=$(tr '\n' ' ' < "build/generatedOutputFile.txt")

    # Now, check if the exact string exists in the file content.
    if [[ ! "$file_content" =~ $search_str ]]; then
		w=80
		printf '%*s\n' "$w" | tr ' ' '#'
		echo "${out}"
		fmt_line "NOT FOUND!"
		printf '%*s\n' "$w" | tr ' ' '#'
    fi
done
print_header "OUTPUT CHECK END"
printf "\n"

print_header "END GRADING"
printf "\n\n"
