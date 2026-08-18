/*
Gate E Conformance Adapter CLI for cortex-go.

Implements the 4-primitive Gate E adapter IPC / CLI protocol:
  - encode <canonical_json>
  - decode <hex_cbe>
  - hash <hex_cbe>
  - uuid <hex_namespace> <hex_cbe>
  - verify (runs Gate E local verification report)
*/
package main

import (
	"encoding/hex"
	"fmt"
	"os"

	"cortex-go/adapter"
	"cortex-go/cbe"
)

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(1)
	}

	cmd := os.Args[1]
	switch cmd {

	case "hash":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Usage: gate-e-adapter hash <hex_cbe_bytes>")
			os.Exit(1)
		}
		cbeBytes, err := hex.DecodeString(os.Args[2])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Invalid hex input: %v\n", err)
			os.Exit(1)
		}
		hash := adapter.ComputeHash(cbeBytes)
		fmt.Println(hash)

	case "uuid":
		if len(os.Args) < 4 {
			fmt.Fprintln(os.Stderr, "Usage: gate-e-adapter uuid <hex_16byte_namespace> <hex_cbe_bytes>")
			os.Exit(1)
		}
		nsBytes, err := hex.DecodeString(os.Args[2])
		if err != nil || len(nsBytes) != 16 {
			fmt.Fprintf(os.Stderr, "Invalid 16-byte hex namespace (must be 32 hex chars): %v\n", err)
			os.Exit(1)
		}
		var ns [16]byte
		copy(ns[:], nsBytes)

		cbeBytes, err := hex.DecodeString(os.Args[3])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Invalid hex payload: %v\n", err)
			os.Exit(1)
		}

		sha1Hex, uuidStr := adapter.DeriveUUID(ns, cbeBytes)
		fmt.Printf("sha1:%s\nuuid:%s\n", sha1Hex, uuidStr)

	case "decode":
		if len(os.Args) < 3 {
			fmt.Fprintln(os.Stderr, "Usage: gate-e-adapter decode <hex_cbe_bytes>")
			os.Exit(1)
		}
		cbeBytes, err := hex.DecodeString(os.Args[2])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Invalid hex input: %v\n", err)
			os.Exit(1)
		}
		val, consumed, err := adapter.DecodeCBE(cbeBytes)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Decode error [%s]: %v\n", cbe.ErrorCode(err), err)
			os.Exit(1)
		}
		fmt.Printf("consumed:%d\ntype:%T\n", consumed, val)

	case "verify":
		fmt.Println("Gate E Go Conformance Adapter initialized. Run 'go test ./tests -v' for full audit trace.")

	default:
		printUsage()
		os.Exit(1)
	}
}

func printUsage() {
	fmt.Println("Gate E Go Conformance Adapter (cortex-go)")
	fmt.Println("Commands:")
	fmt.Println("  hash <hex_cbe>                 Compute standalone SHA-1 digest")
	fmt.Println("  uuid <hex_ns16> <hex_cbe>       Derive SHA-1 and RFC 4122 UUIDv5")
	fmt.Println("  decode <hex_cbe>               Decode CBE bytes to AST")
	fmt.Println("  verify                         Report adapter readiness")
}
