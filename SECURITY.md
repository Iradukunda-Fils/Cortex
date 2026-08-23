# Security Policy

## Supported Versions

| Version | Supported | Notes |
|:---|:---|:---|
| v0.5.x | 🚀 Active Development | Target release for Phase 5 Dynamic Load Balancing |
| v0.4.x | ✅ Active Support | Mainline production candidate baseline |
| v0.3.x | ⚡ Security Patches | Maintenance mode |
| < v0.3.0 | ❌ End of Life | Unsupported legacy release |

## Reporting a Vulnerability

The Cortex project takes security seriously. If you discover a security vulnerability, **please do not open a public GitHub issue.**

### Preferred: GitHub Private Vulnerability Reporting

1. Navigate to the [Security Advisories](https://github.com/Iradukunda-Fils/Cortex/security/advisories) page.
2. Click **"Report a vulnerability"**.
3. Provide a detailed description of the vulnerability, including:
   - Steps to reproduce
   - Affected version(s)
   - Potential impact assessment
   - Suggested fix (if known)

GitHub Security Advisories provide end-to-end encrypted private disclosure directly on the repository.

### Fallback: Email

If you are unable to use GitHub Security Advisories, you may report vulnerabilities via email to the project maintainer. Please include `[SECURITY]` in the subject line.

### What to Expect

- **Acknowledgment**: Within **48 hours** of your report.
- **Initial Assessment**: Within **7 days**, we will provide an initial severity assessment and confirm whether the vulnerability is accepted.
- **Patch Timeline**:
  - **Critical** (sandbox escape, capability bypass, privilege escalation): Target patch within **14 days**.
  - **High** (event forgery, replay divergence): Target patch within **30 days**.
  - **Medium/Low**: Addressed in the next scheduled release.

### Scope

The following categories of issues are considered security vulnerabilities:

| Category | Description |
|:--|:--|
| **Capability Bypass** | Circumventing `CapabilityNegotiator` policy enforcement |
| **Privilege Escalation** | Executing actions beyond granted capability tokens |
| **Sandbox Escape** | Breaking out of `PluginContext` runtime sandbox boundaries |
| **Event Forgery** | Injecting or tampering with events in the `EventStore` |
| **Replay Divergence** | Producing different results on deterministic replay of identical event streams |
| **Resource Exhaustion** | Triggering unbounded CPU, memory, or disk consumption via crafted inputs |

### Out of Scope

- Vulnerabilities in upstream dependencies (report to the respective project)
- Issues in the Coq proof scripts or Rust emulator that do not affect the Python runtime
- Denial-of-service attacks that require local/physical access

## Disclosure Policy

We follow [coordinated vulnerability disclosure](https://en.wikipedia.org/wiki/Coordinated_vulnerability_disclosure). We will:

1. Work with the reporter to understand and validate the issue.
2. Develop and test a fix.
3. Release the fix and publish a security advisory with appropriate credit to the reporter.
4. Allow a reasonable embargo period before public disclosure (typically 90 days from report).

## Credit

We gratefully acknowledge security researchers who responsibly disclose vulnerabilities. With your permission, we will credit you in the security advisory and release notes.
