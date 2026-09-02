/*
 * Cortex Canonical Byte Encoding (CBE) Kernel (Rust Reference Implementation)
 *
 * Implements strict, language-neutral binary serialization, AST node validation,
 * UTF-8 byte map ordering, and RFC 4122 UUIDv5 lineage computation matching Revision #5 spec.
 */

use sha1::{Digest, Sha1};
use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CBEError {
    InvalidUTF8(String),
    NonNFC(String),
    NonCanonicalMap(String),
    DuplicateKey(String),
    FloatNonFinite(String),
    IntOverflow(String),
    InvalidLength(String),
    UnknownTag(String),
}

impl fmt::Display for CBEError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CBEError::InvalidUTF8(msg) => write!(f, "CBEInvalidUTF8Error: {}", msg),
            CBEError::NonNFC(msg) => write!(f, "CBENonNFCError: {}", msg),
            CBEError::NonCanonicalMap(msg) => write!(f, "CBENonCanonicalMapError: {}", msg),
            CBEError::DuplicateKey(msg) => write!(f, "CBEDuplicateKeyError: {}", msg),
            CBEError::FloatNonFinite(msg) => write!(f, "CBEFloatNonFiniteError: {}", msg),
            CBEError::IntOverflow(msg) => write!(f, "CBEIntOverflowError: {}", msg),
            CBEError::InvalidLength(msg) => write!(f, "CBEInvalidLengthError: {}", msg),
            CBEError::UnknownTag(msg) => write!(f, "CBEUnknownTagError: {}", msg),
        }
    }
}

impl std::error::Error for CBEError {}

pub const NAMESPACE_CORTEX_SYSTEM_BYTES: [u8; 16] = [
    0xa1, 0xb2, 0xc3, 0xd4, 0x00, 0x00, 0x50, 0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01,
];

#[derive(Debug, Clone, PartialEq)]
pub enum CortexValue {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    String(String),
    Bytes(Vec<u8>),
    List(Vec<CortexValue>),
    Map(Vec<(String, CortexValue)>),
}

fn to_hex_string(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

pub fn compute_raw_uuidv5(namespace_bytes: &[u8], name_bytes: &[u8]) -> (String, String) {
    let mut hasher = Sha1::new();
    hasher.update(namespace_bytes);
    hasher.update(name_bytes);
    let digest = hasher.finalize();
    let sha1_hex = to_hex_string(digest.as_slice());

    let mut raw_16: [u8; 16] = digest.as_slice()[..16].try_into().unwrap();
    raw_16[6] = (raw_16[6] & 0x0f) | 0x50; // Version 5
    raw_16[8] = (raw_16[8] & 0x3f) | 0x80; // Variant RFC 4122

    let u = uuid::Builder::from_bytes(raw_16).into_uuid();
    (sha1_hex, u.to_string())
}

fn normalize_float(f: f64) -> Result<f64, CBEError> {
    if f.is_nan() || f.is_infinite() {
        return Err(CBEError::FloatNonFinite(format!("Non-finite float: {}", f)));
    }
    if f == 0.0 && f.is_sign_negative() {
        Ok(0.0)
    } else {
        Ok(f)
    }
}

pub fn encode(val: &CortexValue) -> Result<Vec<u8>, CBEError> {
    match val {
        CortexValue::Null => Ok(b"N".to_vec()),
        CortexValue::Bool(b) => {
            if *b {
                Ok(b"B1".to_vec())
            } else {
                Ok(b"B0".to_vec())
            }
        }
        CortexValue::Int(i) => Ok(format!("I{}", i).into_bytes()),
        CortexValue::Float(f) => {
            let f_norm = normalize_float(*f)?;
            let bits = f_norm.to_bits();
            Ok(format!("D{:016x}", bits).into_bytes())
        }
        CortexValue::String(s) => {
            let utf8_bytes = s.as_bytes();
            let mut out = format!("S{}:", utf8_bytes.len()).into_bytes();
            out.extend_from_slice(utf8_bytes);
            Ok(out)
        }
        CortexValue::Bytes(b) => {
            let mut out = format!("B{}:", b.len()).into_bytes();
            out.extend_from_slice(b);
            Ok(out)
        }
        CortexValue::List(items) => {
            let mut out = format!("L{}:", items.len()).into_bytes();
            for item in items {
                out.extend(encode(item)?);
            }
            Ok(out)
        }
        CortexValue::Map(pairs) => {
            let mut pairs_with_bytes: Vec<(&[u8], &String, &CortexValue)> = Vec::new();
            let mut seen_keys: std::collections::HashSet<Vec<u8>> =
                std::collections::HashSet::new();

            for (k, v) in pairs {
                let k_bytes = k.as_bytes();
                if seen_keys.contains(k_bytes) {
                    return Err(CBEError::DuplicateKey(format!("Duplicate key: {:?}", k)));
                }
                seen_keys.insert(k_bytes.to_vec());
                pairs_with_bytes.push((k_bytes, k, v));
            }

            // Canonical sort strictly by UTF-8 bytes of NFC key ("aa" < "b")
            pairs_with_bytes.sort_by(|a, b| a.0.cmp(b.0));

            let mut out = format!("M{}:", pairs_with_bytes.len()).into_bytes();
            for (_bytes, k_str, v_node) in pairs_with_bytes {
                let k_node = CortexValue::String((*k_str).clone());
                out.extend(encode(&k_node)?);
                out.extend(encode(v_node)?);
            }
            Ok(out)
        }
    }
}

pub fn decode(data: &[u8]) -> Result<(CortexValue, usize), CBEError> {
    let tag = *data
        .first()
        .ok_or_else(|| CBEError::InvalidLength("Unexpected end of stream".into()))?;

    match tag {
        b'N' => Ok((CortexValue::Null, 1)),
        b'B' => {
            if data.len() < 2 {
                return Err(CBEError::InvalidLength("Truncated Bool/Bytes tag".into()));
            }
            let next_byte = *data
                .get(1)
                .ok_or_else(|| CBEError::InvalidLength("Truncated Bool/Bytes tag".into()))?;
            if next_byte == b'1' {
                Ok((CortexValue::Bool(true), 2))
            } else if next_byte == b'0' {
                Ok((CortexValue::Bool(false), 2))
            } else {
                // Bytes tag: B<len>:<payload>
                let (len, header_len) = parse_length_prefix(data.get(1..).unwrap_or(&[]))?;
                let start = 1 + header_len;
                if start + len > data.len() {
                    return Err(CBEError::InvalidLength("Truncated Bytes payload".into()));
                }
                let raw_bytes = data
                    .get(start..start + len)
                    .ok_or_else(|| CBEError::InvalidLength("Truncated Bytes payload".into()))?
                    .to_vec();
                Ok((CortexValue::Bytes(raw_bytes), start + len))
            }
        }
        b'I' => {
            let mut curr = 1;
            if curr >= data.len() {
                return Err(CBEError::InvalidLength("Truncated Int stream".into()));
            }
            let is_neg = if data.get(curr) == Some(&b'-') {
                curr += 1;
                true
            } else {
                false
            };

            let start_digits = curr;
            while curr < data.len() && data.get(curr).is_some_and(|b| b.is_ascii_digit()) {
                curr += 1;
            }

            if start_digits == curr {
                return Err(CBEError::InvalidLength("Missing integer digits".into()));
            }

            let digits_bytes = data
                .get(start_digits..curr)
                .ok_or_else(|| CBEError::InvalidLength("Missing integer digits".into()))?;
            let digits_str = std::str::from_utf8(digits_bytes)
                .map_err(|e| CBEError::InvalidUTF8(e.to_string()))?;

            if digits_str.len() > 21 {
                return Err(CBEError::IntOverflow(format!(
                    "Integer digit string exceeds length limit: {}",
                    digits_str.len()
                )));
            }

            if digits_str.len() > 1 && digits_str.starts_with('0') {
                return Err(CBEError::InvalidLength(format!(
                    "Forbidden leading zero in int: {}",
                    digits_str
                )));
            }

            let mut val_int: i64 = digits_str
                .parse()
                .map_err(|_| CBEError::IntOverflow(digits_str.into()))?;
            if is_neg {
                val_int = val_int.wrapping_neg();
            }

            Ok((CortexValue::Int(val_int), curr))
        }
        b'D' => {
            if data.len() < 17 {
                return Err(CBEError::InvalidLength("Truncated Float D tag".into()));
            }
            let hex_bytes = data
                .get(1..17)
                .ok_or_else(|| CBEError::InvalidLength("Truncated Float D tag".into()))?;
            let hex_str =
                std::str::from_utf8(hex_bytes).map_err(|e| CBEError::InvalidUTF8(e.to_string()))?;

            let bits = u64::from_str_radix(hex_str, 16)
                .map_err(|_| CBEError::FloatNonFinite(format!("Invalid float hex: {}", hex_str)))?;

            let val_float = f64::from_bits(bits);
            let norm_float = normalize_float(val_float)?;
            Ok((CortexValue::Float(norm_float), 17))
        }
        b'S' => {
            let (len, header_len) = parse_length_prefix(data.get(1..).unwrap_or(&[]))?;
            let start = 1 + header_len;
            if start + len > data.len() {
                return Err(CBEError::InvalidLength("Truncated String payload".into()));
            }
            let raw_payload = data
                .get(start..start + len)
                .ok_or_else(|| CBEError::InvalidLength("Truncated String payload".into()))?;
            let s = std::str::from_utf8(raw_payload)
                .map_err(|e| CBEError::InvalidUTF8(e.to_string()))?;
            Ok((CortexValue::String(s.to_string()), start + len))
        }
        b'L' => {
            let (count, header_len) = parse_length_prefix(data.get(1..).unwrap_or(&[]))?;
            let mut curr = 1 + header_len;
            let mut items = Vec::with_capacity(count);

            for _ in 0..count {
                let (item, consumed) = decode(data.get(curr..).unwrap_or(&[]))?;
                items.push(item);
                curr += consumed;
            }
            Ok((CortexValue::List(items), curr))
        }
        b'M' => {
            let (count, header_len) = parse_length_prefix(data.get(1..).unwrap_or(&[]))?;
            let mut curr = 1 + header_len;
            let mut pairs = Vec::with_capacity(count);
            let mut prev_key_bytes: Option<Vec<u8>> = None;

            for _ in 0..count {
                let (k_node, k_consumed) = decode(data.get(curr..).unwrap_or(&[]))?;
                curr += k_consumed;

                let k_str = match k_node {
                    CortexValue::String(s) => s,
                    _ => return Err(CBEError::NonCanonicalMap("Map key must be String".into())),
                };

                let curr_key_bytes = k_str.as_bytes().to_vec();
                if let Some(prev) = prev_key_bytes {
                    if curr_key_bytes < prev {
                        return Err(CBEError::NonCanonicalMap(format!(
                            "Unsorted map key encountered: {:?}",
                            k_str
                        )));
                    } else if curr_key_bytes == prev {
                        return Err(CBEError::DuplicateKey(format!(
                            "Duplicate map key encountered: {:?}",
                            k_str
                        )));
                    }
                }
                prev_key_bytes = Some(curr_key_bytes);

                let (v_node, v_consumed) = decode(data.get(curr..).unwrap_or(&[]))?;
                curr += v_consumed;

                pairs.push((k_str, v_node));
            }
            Ok((CortexValue::Map(pairs), curr))
        }
        _ => Err(CBEError::UnknownTag(format!(
            "Unknown tag: {}",
            tag as char
        ))),
    }
}

fn parse_length_prefix(data: &[u8]) -> Result<(usize, usize), CBEError> {
    let mut curr = 0;
    while curr < data.len() && data.get(curr) != Some(&b':') {
        curr += 1;
    }
    if curr >= data.len() {
        return Err(CBEError::InvalidLength(
            "Missing length colon prefix".into(),
        ));
    }
    let slice = data
        .get(..curr)
        .ok_or_else(|| CBEError::InvalidLength("Missing length colon prefix".into()))?;
    let len_str = std::str::from_utf8(slice).map_err(|e| CBEError::InvalidUTF8(e.to_string()))?;
    let len: usize = len_str
        .parse()
        .map_err(|_| CBEError::InvalidLength(len_str.into()))?;
    Ok((len, curr + 1))
}
