#!/usr/bin/env bash

w=80
cd $1
git log -n 3 --pretty=format:"%h %an %ad %s"
cd -
