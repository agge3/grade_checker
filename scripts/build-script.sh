#!/usr/bin/env bash

rm -rf "$1/build"
mkdir -p "$1/build"
cd "$1/build"
cmake ..
make all
"./$2"
cd -
