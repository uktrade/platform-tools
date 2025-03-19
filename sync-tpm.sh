#!/usr/bin/env bash

rsync -r --exclude ".terraform*" ../terraform-platform-modules/* terraform/
