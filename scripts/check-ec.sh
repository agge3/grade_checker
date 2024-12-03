#!/usr/bin/env bash

# Display usage.
usage() {
    echo "Usage: $0 [--gtest] [--templates] [--smart_ptrs] [--help]"
    echo "  --gtest        Count extra credit for GTest"
    echo "  --templates    Count extra credit for templates"
    echo "  --smart_ptrs   Count extra credit for smart pointers (e.g. unique_ptr, shared_ptr)"
    echo "  --help         Display this help message"
    exit 1
}

# Parse command line arguments.
log_gtest=0
log_templates=0
log_smart_ptrs=0
while [[ "$1" =~ ^- ]]; do
    case "$1" in
        --gtest)        log_gtest=1 ;;
        --templates)    log_templates=1 ;;
        --smart_ptrs)   log_smart_ptrs=1 ;;
        --help)         usage ;;
        *)              echo "Invalid option: $1"; usage ;;
    esac
    shift
done

# Extra credit map.
declare -A ec
ec["smart_ptrs"]=0
ec["templates"]=0
ec["gtest"]=0
ec_pts=4

# cpp/hpp files.
hash_fhs=(
    $(grep -i -r -l -E 'hash[- ]?map[- ]?\.(hpp|h|hh)' *)
    $(grep -i -r -l -E 'hash[- ]?map[- ]?\.(cpp|cxx|cc)' *)
)
# Make sure files are found.
if [ ${#hash_fhs[@]} -eq 0 ]; then
    echo "No files found matching the expected file names."
    echo 0
    exit 0
fi

# Search strings.
smart_ptrs=("unique_ptr" "shared_ptr" "weak_ptr" "make_unique" "make_shared")
template="template <typename"

# Loop through the files and look for the search strings. Add extra credit if
# found (only once per instance).
for fh in "${hash_fhs[@]}"
do
    # Add extra credit for smart pointers, if flag set.
    if [ $log_smart_ptrs -eq 1 ]; then
        for ptr in "${smart_ptrs[@]}"
        do
            if grep -q "$ptr" "$fh"; then
                if [ "${ec["smart_ptrs"]}" -eq 0 ]; then
                    ec["smart_ptrs"]=$ec_pts
                fi
                break
            fi
        done
    fi

    # Add extra credit for templates, if flag set.
    if [ $log_templates -eq 1 ]; then
        if grep -q "$template" "$fh"; then
            if [ "${ec["templates"]}" -eq 0 ]; then
                ec["templates"]=$ec_pts
            fi
        fi
    fi

    # Add extra credit for GTest, if flag set.
    if [ $log_gtest -eq 1 ]; then
        if grep -q "#include <gtest/gtest.h>" "$fh" && grep -q "EXPECT_" "$fh"; then
            if [ "${ec["gtest"]}" -eq 0 ]; then
                ec["gtest"]=$ec_pts
            fi
        fi
    fi
done

# Sum the total extra credit.
total=0
for k in "${!ec[@]}"
do
    total=$((total + ec[$k]))
done

# Print total extra credit to stdout.
echo "$total"
