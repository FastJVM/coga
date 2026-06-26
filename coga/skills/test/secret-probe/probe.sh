#!/bin/sh
# Scratch fixture: report which test_* Coga secret keys were injected into the
# script env. Prints KEY NAMES ONLY — never values — so it is safe to run while
# logged/recorded.
echo "=== secret-probe: injected test_* keys (names only, no values) ==="
names=$(env | grep -oE '^test_[A-Za-z0-9_]+' | sort)
if [ -z "$names" ]; then
  echo "  (none injected)"
else
  echo "$names" | sed 's/^/  - /'
fi
echo "=== count: $(env | grep -cE '^test_[A-Za-z0-9_]+=') ==="
