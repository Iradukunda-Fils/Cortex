use crate::isa::CapabilityDescriptor;
use serde::{Deserialize, Serialize};

/// Trap causes according to SDS v1.0 Section 5.1
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TrapCause {
    InvalidValidityBit,
    InsufficientSpatialRights,
    EpochExpired,
    ReservedOpcode(u8),
}

pub struct GuardPipeline;

impl GuardPipeline {
    /// Evaluates spatial and temporal constraints atomically according to SDS v1.0 Section 5.1
    pub fn evaluate_invoke(
        cap: Option<&CapabilityDescriptor>,
        req_perm: u16,
        current_hec: u16,
    ) -> Result<(), TrapCause> {
        let cap = match cap {
            Some(c) if c.valid => c,
            _ => return Err(TrapCause::InvalidValidityBit),
        };

        if (cap.spatial_mask & req_perm) == 0 {
            return Err(TrapCause::InsufficientSpatialRights);
        }

        if current_hec > cap.max_epoch {
            return Err(TrapCause::EpochExpired);
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::isa::spatial_rights;

    #[test]
    fn test_guard_pass() {
        let cap = CapabilityDescriptor::new(
            true,
            spatial_rights::EXEC | spatial_rights::READ,
            0x1000,
            20,
        );
        let res = GuardPipeline::evaluate_invoke(Some(&cap), spatial_rights::EXEC, 15);
        assert_eq!(res, Ok(()));
    }

    #[test]
    fn test_guard_fail_epoch_expired() {
        let cap = CapabilityDescriptor::new(true, spatial_rights::EXEC, 0x1000, 10);
        let res = GuardPipeline::evaluate_invoke(Some(&cap), spatial_rights::EXEC, 15);
        assert_eq!(res, Err(TrapCause::EpochExpired));
    }

    #[test]
    fn test_guard_fail_insufficient_rights() {
        let cap = CapabilityDescriptor::new(true, spatial_rights::READ, 0x1000, 20);
        let res = GuardPipeline::evaluate_invoke(Some(&cap), spatial_rights::WRITE, 15);
        assert_eq!(res, Err(TrapCause::InsufficientSpatialRights));
    }
}
