Require Import RelationClasses.
Require Import Relation_Definitions.

(* ================================================================= *
   MODULE: AuthorityModel.v
   ================================================================= *)

Record Capability := mkCap {
  cap_id : nat;
  cap_max_epoch : nat;
}.

Class AuthorityModel := {
  auth_carrier : Type;
  auth_preorder : relation auth_carrier;
  auth_op : auth_carrier -> auth_carrier -> auth_carrier;
  auth_unit : auth_carrier;
  auth_contains : auth_carrier -> Capability -> Prop;
  
  auth_preorder_rel : PreOrder auth_preorder;
  auth_preorder_monotone : 
    forall x y z, auth_preorder x y -> auth_preorder (auth_op x z) (auth_op y z);
  auth_contains_monotone :
    forall x y c, auth_preorder x y -> auth_contains x c -> auth_contains y c
}.
