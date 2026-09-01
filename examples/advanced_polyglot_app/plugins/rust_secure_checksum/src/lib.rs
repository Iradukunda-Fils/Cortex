#[no_mangle]
pub extern "C" fn rust_fnv1a_hash(data_ptr: *const u8, len: usize) -> u64 {
    if data_ptr.is_null() || len == 0 {
        return 0;
    }
    let slice = unsafe { std::slice::from_raw_parts(data_ptr, len) };
    let mut hash: u64 = 0xcbf29ce484222325;
    for &byte in slice {
        hash ^= byte as u64;
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}
