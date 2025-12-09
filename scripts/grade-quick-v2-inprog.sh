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

#copy_project_fhs ${project_fhs}

cpp_fhs=(
	'doubly linked list'
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

if [[ "${search_dir}" =~ list-(.*) ]]; then
	username="${BASH_REMATCH[1]}"
	print_header "GITHUB USERNAME: ${username}"
else
	echo "XXX GitHub username not found!"
fi

print-git-log
printf "\n"

for fh in ${all_fhs[@]}; do
	print_header "${fh} HEADER"
	sed -n '/\/\*\*/,/\*\//p' "${search_dir}/${fh}"

	print_header "${fh} METHOD CHECK BEGIN"
	for fn in ${methods[@]}; do
		if ! grep -q ${fn} "${search_dir}/${fh}"; then
			echo "${fn} missing!"
		fi
	done
	print_header "${fh} METHOD CHECK END"
done
printf "\n"

print_header "GTEST CHECK"
printf "\n"
if grep -q "#include <gtest/gtest.h>" "${search_dir}/milestone1.cpp" && \
	grep -q "EXPECT_" "${search_dir}/milestone1.cpp"; then
	print_header "FOUND GTEST"
else
	print_header "NO GTEST"
fi
printf "\n"

build()
{
	rm -rf "${search_dir}/build"
	mkdir -p "${search_dir}/build"
	cd "${search_dir}/build"
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
Processing testCase1
Here are the List contents:
Node key: 10
Node key: 20
Node key: 30
Node key: 40
Node key: 50
Node key: 60
Node key: 70
Node key: 80
Node key: 90
Node key: 100
End of List

Here are the List contents reversed:
Node key: 100
Node key: 90
Node key: 80
Node key: 70
Node key: 60
Node key: 50
Node key: 40
Node key: 30
Node key: 20
Node key: 10
End of List	

Successfully processed: testCase1
Processing testCase2
Here are the List contents:
Node key: 1000
Node key: 80
Node key: 50
Node key: 40
End of List

Here are the List contents reversed:
Node key: 40
Node key: 50
Node key: 80
Node key: 1000
End of List

Successfully processed: testCase2

Processing testCase3

Here are the List contents:
Node key: 1000
Node key: 180
Node key: 80
Node key: 40
End of List

Here are the List contents reversed:
Node key: 40
Node key: 80
Node key: 180
Node key: 1000
End of List

Successfully processed: testCase3

Processing testCase4

Here are the List contents:
Node key: 100
Node key: 1000
Node key: 70
Node key: 10
Node key: 40
End of List

Here are the List contents reversed:
Node key: 40
Node key: 10
Node key: 70
Node key: 1000
Node key: 100
End of List

Successfully processed: testCase4

Processing testCase5

Here are the List contents:
Node key: 88
Node key: 80
Node key: 10
Node key: 10000
Node key: 50
End of List

Here are the List contents reversed:
Node key: 50
Node key: 10000
Node key: 10
Node key: 80
Node key: 88
End of List

Successfully processed: testCase5

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
    file_content=$(tr '\n' ' ' < "${search_dir}/build/generatedOutputFile.txt")

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
