#!/usr/bin/env bash
set -euo pipefail

LOG_FILE="audit_results.log"

echo "=================================================================" > "$LOG_FILE"
echo " CORTEX FORMAL MECHANIZATION — KERNEL AUDIT & VERIFICATION LOG " >> "$LOG_FILE"
echo " Generated on: $(date -u)" >> "$LOG_FILE"
echo " Compiler: $(coqc --version | head -n 1)" >> "$LOG_FILE"
echo "=================================================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

echo "=== STEP 1: CLEAN BUILD & COMPILATION ===" >> "$LOG_FILE"
make clean >> "$LOG_FILE" 2>&1 || true
if make >> "$LOG_FILE" 2>&1; then
    echo "[PASS] All modules compiled successfully (exit code 0)." >> "$LOG_FILE"
else
    echo "[FAIL] Compilation error detected during build!" >> "$LOG_FILE"
    exit 1
fi
echo "" >> "$LOG_FILE"

echo "=== STEP 2: SOURCE CODE ADMITTED CHECK ===" >> "$LOG_FILE"
set +e
GREP_OUT=$(grep -rn "Admitted" *.v 2>&1)
GREP_EXIT=$?
set -e

if [ $GREP_EXIT -eq 1 ]; then
    echo "[PASS] Zero 'Admitted' statements found across all .v source files." >> "$LOG_FILE"
else
    echo "[WARNING] Found Admitted statements in source files:" >> "$LOG_FILE"
    echo "$GREP_OUT" >> "$LOG_FILE"
fi
echo "" >> "$LOG_FILE"

echo "=== STEP 3: KERNEL TRANSITIVE DEPENDENCY AUDIT ===" >> "$LOG_FILE"
echo "Running Print Assumptions on core theorems..." >> "$LOG_FILE"

cat << 'EOF' > AuditRunner.v
From Cortex Require Import Soundness.
From Cortex Require Import Substitution.
From Cortex Require Import FTLR.

Print Assumptions unified_soundness.
Print Assumptions fundamental_theorem.
Print Assumptions semantic_substitution_preserves_typing.
Print Assumptions context_weakening.
Print Assumptions V_w_monotonicity.
EOF

coqc -R . Cortex AuditRunner.v >> "$LOG_FILE" 2>&1
rm -f AuditRunner.v AuditRunner.vo AuditRunner.glob AuditRunner.vok AuditRunner.vos

echo "" >> "$LOG_FILE"
echo "=================================================================" >> "$LOG_FILE"
echo " AUDIT COMPLETE — Results written to $LOG_FILE" >> "$LOG_FILE"
echo "=================================================================" >> "$LOG_FILE"

echo "Verification run complete. Displaying audit summary:"
cat "$LOG_FILE"
