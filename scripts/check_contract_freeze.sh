#!/usr/bin/env bash
# Mechanical Spec Freeze Check script for contract specifications

CHANGED_CONTRACT_FILES=$(git diff --cached --name-only | grep "^contracts/commit/spec/")

if [ -n "$CHANGED_CONTRACT_FILES" ]; then
    if ! git log -1 --pretty=%B 2>/dev/null | grep -q "breaking-contract-change"; then
        echo "================================================================="
        echo " ERROR: Modification detected in frozen contract specification!"
        echo " Affected: $CHANGED_CONTRACT_FILES"
        echo " Modifications to contracts/commit/spec/ require an explicit"
        echo " 'breaking-contract-change' commit tag."
        echo "================================================================="
        exit 1
    fi
fi

echo "[✓] Contract spec freeze check passed."
exit 0
