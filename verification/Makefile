# ============================================================
# Cortex Spatiotemporal Authority Verification - Makefile
# ============================================================
# Reproducible build for artifact evaluation.
#
# Requirements: Rocq/Coq >= 9.0
# Usage:
#   make          - Build all verification modules
#   make clean    - Remove compiled artifacts
#   make audit    - Report axiom/admit count across the development
# ============================================================

COQC     := coqc
COQFLAGS := -R . Cortex

# Module dependency order (topologically sorted)
MODULES := AuthorityModel World Semantics LogicalRelation FTLR Substitution Soundness GateF_F0_ModelReconciliation GateF_F1_1_StateCorrespondence GateF_F1_2_StutteringPreservation GateF_F1_2_RealIPC_Stuttering GateF_F2_1_RestrictCap GateF_F2_2_GrantCap GrantCapRTL GateF_F3_1_InvocationSimulation GateL1_EpochMonotonicity

VFILES  := $(addsuffix .v, $(MODULES))
VOFILES := $(addsuffix .vo, $(MODULES))

.PHONY: all clean audit

all: $(VOFILES)
	@echo ""
	@echo "============================================================"
	@echo " BUILD COMPLETE: All modules compiled successfully."
	@echo "============================================================"
	@$(MAKE) --no-print-directory audit

%.vo: %.v
	$(COQC) $(COQFLAGS) $<

# Enforce topological dependency chain
World.vo:                            AuthorityModel.vo
Semantics.vo:                        AuthorityModel.vo World.vo
LogicalRelation.vo:                  AuthorityModel.vo World.vo Semantics.vo
FTLR.vo:                             AuthorityModel.vo World.vo Semantics.vo LogicalRelation.vo
Substitution.vo:                     AuthorityModel.vo World.vo Semantics.vo LogicalRelation.vo FTLR.vo
Soundness.vo:                        AuthorityModel.vo World.vo Semantics.vo LogicalRelation.vo FTLR.vo Substitution.vo
GateF_F0_ModelReconciliation.vo:     AuthorityModel.vo World.vo Semantics.vo
GateF_F1_1_StateCorrespondence.vo:   AuthorityModel.vo World.vo Semantics.vo GateF_F0_ModelReconciliation.vo
GateF_F1_2_StutteringPreservation.vo: AuthorityModel.vo World.vo Semantics.vo GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo
GateF_F1_2_RealIPC_Stuttering.vo:    AuthorityModel.vo World.vo Semantics.vo GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo GateF_F1_2_StutteringPreservation.vo
GateF_F2_1_RestrictCap.vo:           GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo
GateF_F2_2_GrantCap.vo:              GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo GateF_F2_1_RestrictCap.vo
GrantCapRTL.vo:                      GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo GateF_F2_2_GrantCap.vo
GateF_F3_1_InvocationSimulation.vo: GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo GateF_F2_1_RestrictCap.vo GateF_F2_2_GrantCap.vo
GateL1_EpochMonotonicity.vo:         GateF_F0_ModelReconciliation.vo GateF_F1_1_StateCorrespondence.vo GateF_F3_1_InvocationSimulation.vo

clean:
	rm -f *.vo *.vok *.vos *.glob .*.aux

audit:
	@echo ""
	@echo "============================================================"
	@echo " AXIOM / ADMIT AUDIT"
	@echo "============================================================"
	@echo " Axioms:"
	@grep -rn 'Axiom' $(VFILES) || echo "  (none)"
	@echo ""
	@echo " Admitted:"
	@grep -rn 'Admitted' $(VFILES) || echo "  (none)"
	@echo "============================================================"
