Require Import List.
Require Import Arith.
Require Import Ascii.
Import ListNotations.

Require Import Semantics.

Record Program := {
  prog_inst_count : nat;
  prog_instructions : list Instruction
}.

(** Header Constants **)
Definition MAGIC_CORTEX : list byte := 
  [ Byte.of_nat 67; Byte.of_nat 79; Byte.of_nat 82; 
    Byte.of_nat 84; Byte.of_nat 69; Byte.of_nat 88 ]. (* "CORTEX" *)

Definition bytes_to_u16 (b1 b2 : byte) : nat :=
  (Byte.to_nat b1 * 256) + Byte.to_nat b2.

Definition bytes_to_u32 (b1 b2 b3 b4 : byte) : nat :=
  (Byte.to_nat b1 * 16777216) + (Byte.to_nat b2 * 65536) + 
  (Byte.to_nat b3 * 256) + Byte.to_nat b4.

(** 32-Bit Instruction Decoder **)
Definition decode_raw_instruction (raw_u32 : nat) : Instruction :=
  let opcode := Nat.shiftr raw_u32 26 in
  let stcr_id := Nat.land (Nat.shiftr raw_u32 21) 31 in
  let arg_reg := Nat.land (Nat.shiftr raw_u32 16) 31 in
  let imm := Nat.land raw_u32 65535 in
  match opcode with
  | 1 => InstInvoke stcr_id arg_reg
  | 2 => InstGrant stcr_id arg_reg
  | 3 => InstRestrict stcr_id imm
  | 4 => InstRevoke stcr_id
  | 5 => InstHecInc
  | _ => InstReserved opcode (* Explicitly captures illegal opcodes 0x00, 0x06-0x3F *)
  end.

Fixpoint parse_instruction_stream (bytes : list byte) (count : nat) : option (list Instruction) :=
  match count with
  | O => match bytes with [] => Some [] | _ => None end
  | S count' =>
      match bytes with
      | b1 :: b2 :: b3 :: b4 :: rest =>
          let raw := bytes_to_u32 b1 b2 b3 b4 in
          match parse_instruction_stream rest count' with
          | Some insts => Some (decode_raw_instruction raw :: insts)
          | None => None
          end
      | _ => None (* Truncated instruction stream *)
      end
  end.

(** Main Pure Binary Parser **)
Definition load_program (bytes : list byte) : option Program :=
  match bytes with
  | m0 :: m1 :: m2 :: m3 :: m4 :: m5 :: v0 :: v1 :: c0 :: c1 :: c2 :: c3 :: payload =>
      if list_eq_dec Byte.eq_dec [m0; m1; m2; m3; m4; m5] MAGIC_CORTEX then
        if Nat.eqb (bytes_to_u16 v0 v1) 1 then
          let count := bytes_to_u32 c0 c1 c2 c3 in
          match parse_instruction_stream payload count with
          | Some insts => Some {| prog_inst_count := count; prog_instructions := insts |}
          | None => None
          end
        else None (* Unsupported version *)
      else None (* Invalid magic header *)
  | _ => None (* Binary header truncated *)
  end.
