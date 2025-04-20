#!/usr/bin/env bash

# Get all directories in pwd.
dirs=($(ls -d */))

excl=(
	'project_fhs'
	'source_dir'
)

# Loop through each directory.
for (( i = 0; i < ${#dirs[@]}; i++ )); do
    dir="${dirs[$i]%/}"  # Remove trailing slash from the directory name.
	# Skip directory if it's in the exclude list.
	for ex in ${excl[@]}; do
		if [[ ${dir} == ${ex} ]]; then
			continue 2
		fi
	done

	# Get name for output file.
	if [[ ${dir} =~ list-(.*) ]]; then
		name="${BASH_REMATCH[1]}"
		echo "XXX ${name}"
	else
		name="XXX"
	fi

    # Run grade-quick.sh for the directory and append to name_output.txt.
	#printf "GRADE REPORT\n\n" > "${name}_output.txt"
    ./grade-quick.sh "$dir" >> "${name}_output.txt"
done
