/*
 * Phase 2 Rust CBE Conformance Integration Test Suite (Hardened)
 *
 * MANDATORY GOVERNANCE COMPLIANCE:
 * 1. MANIFEST PROVENANCE & READ-ONLY HARD LOCK:
 *    - Validates SHA-256 of all frozen artifact files against pre-existing frozen constants.
 *    - Aborts immediately if any artifact has been altered or regenerated.
 * 2. ZERO PYTHON DEPENDENCY:
 *    - Pure Rust execution via cargo test with no FFI or subprocess calls.
 * 3. CRYPTOGRAPHIC INPUT PROVENANCE:
 *    - Computes and prints exact SHA-1 preimage trace (Namespace_Bytes || CBE_Bytes).
 *    - Verifies manual SHA-1 + RFC 4122 bit-masking matches `uuid::Uuid::new_v5` verbatim.
 */

use cortex_emulator::cbe::{
    compute_raw_uuidv5, decode, encode, CBEError, CortexValue, NAMESPACE_CORTEX_SYSTEM_BYTES,
};
use sha2::{Digest as Sha2Digest, Sha256};
use std::fs;
use std::path::PathBuf;

// Pre-existing frozen SHA-256 manifest constants (Oracle Oracle)
const FROZEN_MANIFEST_SHA256: &[(&str, &str)] = &[
    (
        "tv-a.cbe",
        "64b199ea01a788553cc95b193629d25d46b03f76f960b1d4f50ac420f82f4125",
    ),
    (
        "tv-a.sha1",
        "9602e438601eaf9f570ae7fc98854a9adaca30ffb1c74e3705cf6a3301c4c341",
    ),
    (
        "tv-a.uuid",
        "3d6ec74d4f9c482d54a9b8710a0a8751c8c46fa24c59467a8611778b10ed6f8e",
    ),
    (
        "tv-b.cbe",
        "6bb283fc20ae27e2f793c21e8d2d2264a6fb0fda7ba73e4544d1ded09bd8e512",
    ),
    (
        "tv-b.sha1",
        "48f6c6c9111de3084b8812263ddf4f1f2c81cc9ce5bef2b4fce363897d0981c0",
    ),
    (
        "tv-b.uuid",
        "625634e04dfd4727a51c778dc7c78cc5159500112accb221590ac37c9d5940eb",
    ),
    (
        "tv-c.cbe",
        "96cac57eb5941a8ec367ffe5e98bbff061858cc8387fa404cb5d9ad428151cbf",
    ),
    (
        "tv-c.sha1",
        "a70e80615ad52d01b1e95f198b667b5dfd62827e9555c4359d8a5cce335d3a88",
    ),
    (
        "tv-c.uuid",
        "15034006695120f7cec81617c463653a1353e347f92e9111df16fadabee84336",
    ),
    (
        "tv-root.cbe",
        "86fad8e2978d61dcef218a1eb6fce53a39913f040a60eec71eafaad231e1d589",
    ),
    (
        "tv-root.sha1",
        "c786cbdb18eea02e56546dd8282ccec91471fe7c3ab21af16efa32eca0976002",
    ),
    (
        "tv-root.uuid",
        "4a6455bfe447f0e36386f7e19d854e4d8b4b1bd8393ac72b17e09318d3036a62",
    ),
];

fn get_artifact_dir() -> PathBuf {
    let mut path = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    path.push("..");
    path.push("research");
    path.push("formalization");
    path.push("artifacts");
    path
}

fn to_hex_string(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

fn verify_manifest_integrity() {
    let dir = get_artifact_dir();
    for (filename, expected_sha256) in FROZEN_MANIFEST_SHA256 {
        let file_path = dir.join(filename);
        let content = fs::read(&file_path).unwrap_or_else(|_| {
            panic!(
                "MANIFEST INTEGRITY ERROR: Missing artifact file {:?}",
                file_path
            )
        });
        let mut hasher = Sha256::new();
        hasher.update(&content);
        let actual_sha256 = to_hex_string(&hasher.finalize());
        assert_eq!(
            &actual_sha256, expected_sha256,
            "MANIFEST INTEGRITY FAILURE: Frozen artifact {} has been modified! Expected {}, got {}",
            filename, expected_sha256, actual_sha256
        );
    }
    println!("[✓] MANIFEST ANTI-CIRCULARITY CHECK PASSED: All 12 artifact files match frozen SHA-256 oracle.");
}

fn test_vector_conformance(name: &str) -> (String, usize, String, String, String, bool) {
    verify_manifest_integrity();
    let dir = get_artifact_dir();

    let cbe_path = dir.join(format!("{}.cbe", name));
    let sha1_path = dir.join(format!("{}.sha1", name));
    let uuid_path = dir.join(format!("{}.uuid", name));

    let expected_cbe_bytes = fs::read(&cbe_path)
        .unwrap_or_else(|_| panic!("Failed to read CBE artifact at {:?}", cbe_path));

    let expected_sha1_content = fs::read_to_string(&sha1_path)
        .unwrap_or_else(|_| panic!("Failed to read SHA1 artifact at {:?}", sha1_path));
    let expected_sha1_hex = expected_sha1_content.lines().next().unwrap().trim();

    let expected_uuid_content = fs::read_to_string(&uuid_path)
        .unwrap_or_else(|_| panic!("Failed to read UUID artifact at {:?}", uuid_path));
    let expected_uuid_str = expected_uuid_content.trim();

    // 1. Calculate CBE SHA-256
    let mut cbe_hasher = Sha256::new();
    cbe_hasher.update(&expected_cbe_bytes);
    let cbe_sha256_hex = to_hex_string(&cbe_hasher.finalize());

    // 2. Decode wire bytes to AST
    let (ast_node, consumed_bytes) = decode(&expected_cbe_bytes)
        .unwrap_or_else(|e| panic!("Failed to decode {} wire bytes: {}", name, e));

    assert_eq!(
        consumed_bytes,
        expected_cbe_bytes.len(),
        "{} decoder did not consume total payload bytes",
        name
    );

    // 3. Re-encode AST and check exact byte match
    let re_encoded_bytes =
        encode(&ast_node).unwrap_or_else(|e| panic!("Failed to re-encode {} AST: {}", name, e));

    assert_eq!(
        re_encoded_bytes, expected_cbe_bytes,
        "{} CBE byte mismatch!",
        name
    );

    // 4. Cryptographic Input Provenance Trace
    let mut preimage_bytes = Vec::new();
    preimage_bytes.extend_from_slice(&NAMESPACE_CORTEX_SYSTEM_BYTES);
    preimage_bytes.extend_from_slice(&expected_cbe_bytes);
    let preimage_hex = to_hex_string(&preimage_bytes);

    let (computed_sha1_hex, computed_uuid_str) =
        compute_raw_uuidv5(&NAMESPACE_CORTEX_SYSTEM_BYTES, &expected_cbe_bytes);

    // Verify crate uuid::Uuid::new_v5 produces identical output to manual computation
    let ns_uuid = uuid::Uuid::from_bytes(NAMESPACE_CORTEX_SYSTEM_BYTES);
    let crate_uuid_v5 = uuid::Uuid::new_v5(&ns_uuid, &expected_cbe_bytes).to_string();

    assert_eq!(
        computed_sha1_hex, expected_sha1_hex,
        "{} SHA1 hex mismatch!",
        name
    );
    assert_eq!(
        computed_uuid_str, expected_uuid_str,
        "{} Manual UUIDv5 string mismatch!",
        name
    );
    assert_eq!(
        crate_uuid_v5, expected_uuid_str,
        "{} Crate Uuid::new_v5 mismatch!",
        name
    );

    println!("============================================================");
    println!("CRYPTOGRAPHIC INPUT PROVENANCE PROOF: {}", name);
    println!(
        "  namespace_hex:                   {}",
        to_hex_string(&NAMESPACE_CORTEX_SYSTEM_BYTES)
    );
    println!(
        "  cbe_hex:                         {}",
        to_hex_string(&expected_cbe_bytes)
    );
    println!("  concatenated_sha1_preimage_hex:  {}", preimage_hex);
    println!("  sha1_digest_hex:                 {}", computed_sha1_hex);
    println!("  frozen_uuid:                     {}", expected_uuid_str);
    println!("  rust_derived_uuid:               {}", computed_uuid_str);
    println!("  crate_uuid_v5:                   {}", crate_uuid_v5);
    println!("  exact_match:                     PASS");
    println!("============================================================");

    (
        cbe_sha256_hex,
        expected_cbe_bytes.len(),
        computed_sha1_hex,
        expected_uuid_str.to_string(),
        computed_uuid_str,
        true,
    )
}

#[test]
fn test_vector_tv_a() {
    let (_, _, _, _, _, pass) = test_vector_conformance("tv-a");
    assert!(pass);
}

#[test]
fn test_vector_tv_b() {
    let (_, _, _, _, _, pass) = test_vector_conformance("tv-b");
    assert!(pass);
}

#[test]
fn test_vector_tv_c() {
    let (_, _, _, _, _, pass) = test_vector_conformance("tv-c");
    assert!(pass);
}

#[test]
fn test_vector_tv_root() {
    let (_, _, _, _, _, pass) = test_vector_conformance("tv-root");
    assert!(pass);
}

#[test]
fn test_adversarial_non_canonical_map_rejection() {
    let malformed_wire = b"M2:S1:bI1S2:aaI2";
    let res = decode(malformed_wire);
    assert!(res.is_err());
    match res.err().unwrap() {
        CBEError::NonCanonicalMap(msg) => {
            assert!(msg.contains("Unsorted map key encountered"));
        }
        other => panic!("Expected NonCanonicalMap error, got {:?}", other),
    }
}

#[test]
fn test_adversarial_duplicate_key_rejection() {
    let duplicate_map_ast = CortexValue::Map(vec![
        ("key".to_string(), CortexValue::Int(1)),
        ("key".to_string(), CortexValue::Int(2)),
    ]);
    let res = encode(&duplicate_map_ast);
    assert!(res.is_err());
    match res.err().unwrap() {
        CBEError::DuplicateKey(msg) => {
            assert!(msg.contains("Duplicate key"));
        }
        other => panic!("Expected DuplicateKey error, got {:?}", other),
    }
}

#[test]
fn test_adversarial_non_finite_float_rejection() {
    let nan_val = CortexValue::Float(f64::NAN);
    let res = encode(&nan_val);
    assert!(res.is_err());
    match res.err().unwrap() {
        CBEError::FloatNonFinite(_) => {}
        other => panic!("Expected FloatNonFinite error, got {:?}", other),
    }
}

#[test]
fn test_adversarial_integer_overflow_rejection() {
    let malformed_int_wire = b"I12345678901234567890123";
    let res = decode(malformed_int_wire);
    assert!(res.is_err());
    match res.err().unwrap() {
        CBEError::IntOverflow(msg) => {
            assert!(msg.contains("length limit"));
        }
        other => panic!("Expected IntOverflow error, got {:?}", other),
    }
}
