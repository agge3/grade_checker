#!/usr/bin/env bash

for d in */; do
	cd "$d"
	rm -rvf dll_node.cpp
	rm -rvf dll_node.h
	rm -rvf doubly_linked_list.h
	rm -rvf milestone1_config.json
	rm -rvf milestone1.cpp
	rm -rvf milestone1.json
	cd ..
done
