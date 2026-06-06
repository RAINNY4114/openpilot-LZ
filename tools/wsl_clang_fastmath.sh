#!/usr/bin/env bash
set -e

exec clang -ffast-math "$@"
