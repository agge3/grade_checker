#!/usr/bin/env bash

repo=$1

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
