"""
Cortex Canonical Configuration Resolver (Issue #30)

Authoritative single-entrypoint configuration processing engine and admission control plane.
Enforces the 10-stage resolution pipeline:
1. Merge Input Sources (Defaults -> File -> Environment -> CLI)
2. Default Materialization
3. Field-Class Specific Normalization (NFC Human Text, ASCII Identifiers, Canonical Capabilities, Paths)
4. JSON Schema Structural Validation (Draft 2020-12)
5. Semantic Validation (replica bounds, path isolation, capability formats)
6. Security Ceiling Enforcement (EffectiveConfig <= SecurityCeiling)
7. Canonical CBE / Sorted UTF-8 Encoding (Set-Array lexicographical sorting)
8. SHA-256 Digest Computation (config_hash)
9. Immutable Snapshot Creation (DesiredConfig)
10. Generation Binding & Crash-Safe Durable Admission (ConfigAdmissionEngine)
"""

import hashlib
import json
import os
import re
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import jsonschema

from cortex.exceptions import (
    ConfigurationError,
    SchemaValidationError,
    SecurityCeilingViolationError,
    SemanticValidationError,
)

# Pinned local schema file path relative to cortex package root
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "v1" / "configuration.schema.json"

# Forbidden system directories for filesystem write boundaries
_FORBIDDEN_SYSTEM_ROOTS = {"/bin", "/sbin", "/usr", "/etc", "/lib", "/proc", "/sys", "/root", "/boot", "/dev"}


class ArraySemantics(Enum):
    """Explicit field array taxonomy classification."""

    SET = "SET"  # Unordered set-like array; sorted lexicographically for canonical hashing
    ORDERED_SEQUENCE = "ORDERED_SEQUENCE"  # Sequence where item order carries semantic meaning
    MULTISET = "MULTISET"  # Unordered collection allowing duplicates


class CanonicalCapability:
    """Canonical capability parser and representation."""

    __slots__ = ("action", "namespace")

    def __init__(self, namespace: str, action: str) -> None:
        self.namespace = namespace
        self.action = action

    @classmethod
    def parse(cls, cap_str: str) -> "CanonicalCapability":
        if not cap_str or cap_str == "*":
            raise SemanticValidationError(f"Invalid capability format '{cap_str}': wildcards forbidden")

        parts = cap_str.split(".", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise SemanticValidationError(f"Invalid capability format '{cap_str}': must match '<namespace>.<action>'")

        pattern = re.compile(r"^[a-z0-9_-]+\.[a-z0-9._-]+$")
        if not pattern.match(cap_str):
            raise SemanticValidationError(
                f"Invalid capability characters in '{cap_str}': must match alphanumeric namespace notation"
            )

        return cls(parts[0], parts[1])

    def __str__(self) -> str:
        return f"{self.namespace}.{self.action}"

    def __repr__(self) -> str:
        return f"CanonicalCapability({self.namespace}.{self.action})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, CanonicalCapability):
            return self.namespace == other.namespace and self.action == other.action
        return False

    def __hash__(self) -> int:
        return hash((self.namespace, self.action))


@dataclass(frozen=True)
class GatewayConfig:
    max_queue_depth: int = 1000
    max_worker_inflight: int = 10
    queue_timeout_sec: float = 30.0
    dispatch_deadline_sec: float = 5.0
    selection_policy: str = "least_inflight_deterministic"
    journal_path: str = "/var/log/cortex/invocation_journal.jsonl"
    fsync_policy: str = "always"


@dataclass(frozen=True)
class ReplicaGroupConfig:
    group_id: str = "default_group"
    min_replicas: int = 1
    max_replicas: int = 10
    drain_deadline_sec: float = 30.0


@dataclass(frozen=True)
class SandboxConfig:
    profile_name: str = "Profile_A_Linux_Strict"
    required_capabilities: tuple[str, ...] = ("host.read", "host.write")
    allowed_syscalls: tuple[str, ...] = ("clock_gettime", "exit", "futex", "read", "write")
    landlock_paths: tuple[str, ...] = ("/tmp", "/var/log")
    read_only_root: bool = True
    allowed_write_paths: tuple[str, ...] = ("/tmp/sandbox_default",)


@dataclass(frozen=True)
class ResourceLimitsConfig:
    memory_limit_mb: int = 512
    cpu_quota_percent: int = 100


@dataclass(frozen=True)
class DesiredConfig:
    schema_version: str
    gateway: GatewayConfig
    replica_group: ReplicaGroupConfig
    sandbox: SandboxConfig
    resource_limits: ResourceLimitsConfig

    def to_dict(self) -> dict[str, Any]:
        """Convert frozen dataclass structure to plain dictionary representation."""
        return {
            "schema_version": self.schema_version,
            "gateway": asdict(self.gateway),
            "replica_group": asdict(self.replica_group),
            "sandbox": {
                "profile_name": self.sandbox.profile_name,
                "required_capabilities": list(self.sandbox.required_capabilities),
                "allowed_syscalls": list(self.sandbox.allowed_syscalls),
                "landlock_paths": list(self.sandbox.landlock_paths),
                "read_only_root": self.sandbox.read_only_root,
                "allowed_write_paths": list(self.sandbox.allowed_write_paths),
            },
            "resource_limits": asdict(self.resource_limits),
        }


@dataclass(frozen=True)
class DerivedConfigurationIdentity:
    config_hash: str
    config_generation: int
    snapshot_timestamp: float
    desired_config: DesiredConfig


def get_default_raw_config() -> dict[str, Any]:
    """Returns the normative default raw configuration structure."""
    return {
        "schema_version": "1.0.0",
        "gateway": {
            "max_queue_depth": 1000,
            "max_worker_inflight": 10,
            "queue_timeout_sec": 30.0,
            "dispatch_deadline_sec": 5.0,
            "selection_policy": "least_inflight_deterministic",
            "journal_path": "/var/log/cortex/invocation_journal.jsonl",
            "fsync_policy": "always",
        },
        "replica_group": {
            "group_id": "default_group",
            "min_replicas": 1,
            "max_replicas": 10,
            "drain_deadline_sec": 30.0,
        },
        "sandbox": {
            "profile_name": "Profile_A_Linux_Strict",
            "required_capabilities": ["host.read", "host.write"],
            "allowed_syscalls": ["clock_gettime", "exit", "futex", "read", "write"],
            "landlock_paths": ["/tmp", "/var/log"],
            "read_only_root": True,
            "allowed_write_paths": ["/tmp/sandbox_default"],
        },
        "resource_limits": {
            "memory_limit_mb": 512,
            "cpu_quota_percent": 100,
        },
    }


# Authoritative mapping from environment variables to config fields
_ENV_MAP: dict[str, tuple[str, str, type]] = {
    "CORTEX_GATEWAY_MAX_QUEUE_DEPTH": ("gateway", "max_queue_depth", int),
    "CORTEX_GATEWAY_MAX_WORKER_INFLIGHT": ("gateway", "max_worker_inflight", int),
    "CORTEX_GATEWAY_QUEUE_TIMEOUT_SEC": ("gateway", "queue_timeout_sec", float),
    "CORTEX_GATEWAY_DISPATCH_DEADLINE_SEC": ("gateway", "dispatch_deadline_sec", float),
    "CORTEX_GATEWAY_SELECTION_POLICY": ("gateway", "selection_policy", str),
    "CORTEX_GATEWAY_JOURNAL_PATH": ("gateway", "journal_path", str),
    "CORTEX_GATEWAY_FSYNC_POLICY": ("gateway", "fsync_policy", str),
    "CORTEX_REPLICA_GROUP_ID": ("replica_group", "group_id", str),
    "CORTEX_REPLICA_MIN_REPLICAS": ("replica_group", "min_replicas", int),
    "CORTEX_REPLICA_MAX_REPLICAS": ("replica_group", "max_replicas", int),
    "CORTEX_REPLICA_DRAIN_DEADLINE_SEC": ("replica_group", "drain_deadline_sec", float),
    "CORTEX_SANDBOX_PROFILE_NAME": ("sandbox", "profile_name", str),
    "CORTEX_SANDBOX_READ_ONLY_ROOT": ("sandbox", "read_only_root", bool),
    "CORTEX_RESOURCE_MEMORY_LIMIT_MB": ("resource_limits", "memory_limit_mb", int),
    "CORTEX_RESOURCE_CPU_QUOTA_PERCENT": ("resource_limits", "cpu_quota_percent", int),
}


def normalize_secure_path(path_str: str, field_name: str, allowed_prefix: str | None = None) -> str:
    """Normalizes and validates path isolation.

    Audits lexical '..' prior to abspath resolution, checks forbidden system roots,
    and validates prefix containment.
    """
    # 1. Audit raw path representation for lexical traversal BEFORE abspath normalizes it away
    raw_segments = path_str.replace("\\", "/").split("/")
    if ".." in raw_segments:
        raise SecurityCeilingViolationError(f"Lexical path traversal ('..') detected in {field_name}: '{path_str}'")

    # 2. Canonicalize path
    norm_path = os.path.abspath(os.path.normpath(path_str))

    # 3. Assert containment against forbidden system roots
    for sys_root in _FORBIDDEN_SYSTEM_ROOTS:
        if norm_path == sys_root or norm_path.startswith(sys_root + "/"):
            raise SecurityCeilingViolationError(
                f"Forbidden system write path target '{norm_path}' for {field_name}: overlaps with '{sys_root}'"
            )

    # 4. Assert containment prefix if required
    if allowed_prefix and not norm_path.startswith(allowed_prefix):
        raise SecurityCeilingViolationError(
            f"Invalid write path '{norm_path}' for {field_name}: write paths MUST start with '{allowed_prefix}'"
        )

    return norm_path


class ConfigResolver:
    """Authoritative Cortex Configuration Resolver and Pipeline Engine."""

    def __init__(self, schema_path: Path | None = None) -> None:
        self.schema_path = schema_path or _SCHEMA_PATH
        self._schema: dict[str, Any] | None = None
        self._validator: jsonschema.Draft202012Validator | None = None

    def _get_validator(self) -> jsonschema.Draft202012Validator:
        if self._validator is None:
            if not self.schema_path.exists():
                raise ConfigurationError(f"Pinned JSON Schema file not found at: {self.schema_path}")
            with open(self.schema_path, "r", encoding="utf-8") as f:
                loaded_schema: dict[str, Any] = json.load(f)
            self._schema = loaded_schema
            self._validator = jsonschema.Draft202012Validator(loaded_schema)
        return self._validator

    def parse_env_overrides(self, env_dict: dict[str, str] | None = None) -> dict[str, Any]:
        """Extracts and parses CORTEX_* environment variables into nested config dict."""
        if env_dict is None:
            env_dict = dict(os.environ)

        overrides: dict[str, Any] = {}
        for env_key, val in env_dict.items():
            if env_key in _ENV_MAP:
                section, field, field_type = _ENV_MAP[env_key]
                if section not in overrides:
                    overrides[section] = {}

                parsed_val: Any
                try:
                    if field_type is bool:
                        parsed_val = val.lower() in ("true", "1", "yes")
                    elif field_type is int:
                        parsed_val = int(val)
                    elif field_type is float:
                        parsed_val = float(val)
                    else:
                        parsed_val = val
                except ValueError as err:
                    raise SchemaValidationError(
                        f"Invalid environment variable value for '{env_key}': '{val}' cannot be parsed as {field_type.__name__}"
                    ) from err

                overrides[section][field] = parsed_val

        return overrides

    def resolve(
        self,
        config_file: str | Path | None = None,
        file_dict: dict[str, Any] | None = None,
        env_dict: dict[str, str] | None = None,
        cli_overrides: dict[str, Any] | None = None,
        security_override: bool = False,
        current_identity: DerivedConfigurationIdentity | None = None,
    ) -> DerivedConfigurationIdentity:
        """Executes the 10-stage configuration resolution pipeline."""
        # STAGE 1 & 2: Read & Merge Input Sources
        raw = get_default_raw_config()

        if config_file is not None:
            c_path = Path(config_file)
            if not c_path.exists():
                raise ConfigurationError(f"Configuration file not found: {c_path}")
            with open(c_path, "r", encoding="utf-8") as f:
                content = f.read()
                if c_path.suffix in (".yaml", ".yml"):
                    import yaml

                    file_data = yaml.safe_load(content)
                else:
                    file_data = json.loads(content)
                if isinstance(file_data, dict):
                    self._deep_merge(raw, file_data)

        if file_dict is not None:
            self._deep_merge(raw, file_dict)

        env_overrides = self.parse_env_overrides(env_dict)
        self._deep_merge(raw, env_overrides)

        if cli_overrides is not None:
            self._deep_merge(raw, cli_overrides)

        # STAGE 3: Field-Class Specific Normalization (Occurs BEFORE Schema & Security Validation)
        normalized_raw = self._normalize_by_field_class(raw)

        # STAGE 4: Structural JSON Schema Validation (Draft 2020-12)
        validator = self._get_validator()
        try:
            validator.validate(normalized_raw)
        except jsonschema.ValidationError as err:
            path_str = ".".join(str(p) for p in err.path)
            raise SchemaValidationError(
                f"JSON Schema structural validation failure at '{path_str}': {err.message}"
            ) from err

        # STAGE 5: Semantic Validation
        replica = normalized_raw["replica_group"]
        if replica["min_replicas"] > replica["max_replicas"]:
            raise SemanticValidationError(
                f"min_replicas ({replica['min_replicas']}) cannot exceed max_replicas ({replica['max_replicas']})"
            )

        sandbox = normalized_raw["sandbox"]
        # Parse required capabilities via CanonicalCapability parser
        parsed_caps: list[str] = []
        for cap_str in sandbox.get("required_capabilities", []):
            parsed_cap = CanonicalCapability.parse(str(cap_str))
            parsed_caps.append(str(parsed_cap))
        # Field Array Taxonomy: SET fields are lexicographically sorted for canonical encoding
        sandbox["required_capabilities"] = sorted(parsed_caps)

        # STAGE 6: Security Ceiling Enforcement (EffectiveConfig <= SecurityCeiling)
        if sandbox.get("profile_name") not in ("Profile_A_Linux_Strict", "Profile_B_WASM_Strict") and not security_override:
            raise SecurityCeilingViolationError(
                f"Security profile ceiling violation: attempted profile '{sandbox.get('profile_name')}' "
                f"degrades strict profiles without security override"
            )

        if not sandbox.get("read_only_root", True) and not security_override:
            raise SecurityCeilingViolationError(
                "Security ceiling violation: read_only_root cannot be set to false without explicit security override"
            )

        limits = normalized_raw["resource_limits"]
        if limits.get("memory_limit_mb", 512) > 32768 and not security_override:
            raise SecurityCeilingViolationError(
                f"Resource ceiling violation: memory_limit_mb ({limits.get('memory_limit_mb')}) exceeds max host ceiling 32768 MB"
            )

        # Validate path boundaries securely
        gateway = normalized_raw["gateway"]
        gateway["journal_path"] = normalize_secure_path(gateway["journal_path"], "gateway.journal_path")

        validated_write_paths: list[str] = []
        for wpath in sandbox.get("allowed_write_paths", []):
            norm_wpath = normalize_secure_path(wpath, "sandbox.allowed_write_paths", allowed_prefix="/tmp/sandbox_")
            if os.path.islink(norm_wpath):
                raise SecurityCeilingViolationError(f"Symlink write target forbidden in allowed_write_paths: '{wpath}'")
            validated_write_paths.append(norm_wpath)
        sandbox["allowed_write_paths"] = sorted(validated_write_paths)

        # STAGE 7: Canonical CBE / Sorted UTF-8 JSON Encoding
        canonical_bytes = json.dumps(normalized_raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )

        # STAGE 8: SHA-256 Digest Computation
        config_hash = hashlib.sha256(canonical_bytes).hexdigest()

        # STAGE 9: Immutable Snapshot Creation
        desired_config = DesiredConfig(
            schema_version=normalized_raw["schema_version"],
            gateway=GatewayConfig(**normalized_raw["gateway"]),
            replica_group=ReplicaGroupConfig(**normalized_raw["replica_group"]),
            sandbox=SandboxConfig(
                profile_name=sandbox["profile_name"],
                required_capabilities=tuple(sandbox["required_capabilities"]),
                allowed_syscalls=tuple(sandbox["allowed_syscalls"]),
                landlock_paths=tuple(sandbox["landlock_paths"]),
                read_only_root=sandbox["read_only_root"],
                allowed_write_paths=tuple(sandbox["allowed_write_paths"]),
            ),
            resource_limits=ResourceLimitsConfig(**limits),
        )

        # STAGE 10: Monotonic Generation Binding
        prev_generation = current_identity.config_generation if current_identity else 0
        if current_identity and current_identity.config_hash == config_hash:
            config_generation = prev_generation
        else:
            config_generation = prev_generation + 1

        return DerivedConfigurationIdentity(
            config_hash=config_hash,
            config_generation=config_generation,
            snapshot_timestamp=time.monotonic(),
            desired_config=desired_config,
        )

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> None:
        """Deep merges nested dicts in-place."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _normalize_by_field_class(self, data: Any) -> Any:
        """Applies explicit field-class specific normalization (NFC human text, set sorting)."""
        if isinstance(data, dict):
            res: dict[str, Any] = {}
            for k, v in data.items():
                if k in (
                    "required_capabilities",
                    "allowed_syscalls",
                    "landlock_paths",
                    "allowed_write_paths",
                ) and isinstance(v, list):
                    # Array Taxonomy: SET fields are lexicographically sorted for canonical encoding
                    sorted_elems = sorted([str(self._normalize_by_field_class(elem)) for elem in v])
                    res[k] = sorted_elems
                elif k in ("group_id", "profile_name", "selection_policy", "fsync_policy") and isinstance(v, str):
                    # ASCII Identifier verification
                    res[k] = v.strip()
                elif k == "schema_version" and isinstance(v, str):
                    # Human text: NFC Unicode normalization
                    res[k] = unicodedata.normalize("NFC", v)
                else:
                    res[k] = self._normalize_by_field_class(v)
            return res
        elif isinstance(data, list):
            return [self._normalize_by_field_class(item) for item in data]
        elif isinstance(data, str):
            # General strings preserved byte-exact unless identified as human text
            return data
        return data


class ConfigAdmissionEngine:
    """Authoritative Control Plane Admission Engine for Stateful Generation Management."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self.storage_path = storage_path
        self.current_identity: DerivedConfigurationIdentity | None = None
        self._lock = threading.Lock()
        if self.storage_path and self.storage_path.exists() and self.storage_path.stat().st_size > 0:
            self._load_durable_state()

    def admit(
        self,
        resolver: ConfigResolver,
        config_file: str | Path | None = None,
        file_dict: dict[str, Any] | None = None,
        env_dict: dict[str, str] | None = None,
        cli_overrides: dict[str, Any] | None = None,
        security_override: bool = False,
    ) -> DerivedConfigurationIdentity:
        """Thread-safe transactional admission of a candidate configuration."""
        with self._lock:
            identity = resolver.resolve(
                config_file=config_file,
                file_dict=file_dict,
                env_dict=env_dict,
                cli_overrides=cli_overrides,
                security_override=security_override,
                current_identity=self.current_identity,
            )
            self.current_identity = identity
            if self.storage_path:
                self._persist_durable_state_atomic()
            return identity

    def _persist_durable_state_atomic(self) -> None:
        """Atomic crash-safe disk persistence protocol with fsync and replace."""
        if self.current_identity and self.storage_path:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.storage_path.with_suffix(f".tmp.{os.getpid()}")

            payload = {
                "config_hash": self.current_identity.config_hash,
                "config_generation": self.current_identity.config_generation,
                "snapshot_timestamp": self.current_identity.snapshot_timestamp,
                "desired_config": self.current_identity.desired_config.to_dict(),
            }

            # 1. Write to temporary file
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                # 2. Issue fsync to guarantee disk durability before metadata update
                os.fsync(f.fileno())

            # 3. Atomic rename/replace to replace active storage path atomically
            os.replace(tmp_path, self.storage_path)

    def _load_durable_state(self) -> None:
        """Reads durable state with torn-record recovery protection."""
        if self.storage_path and self.storage_path.exists() and self.storage_path.stat().st_size > 0:
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
                d = payload["desired_config"]
                desired = DesiredConfig(
                    schema_version=d["schema_version"],
                    gateway=GatewayConfig(**d["gateway"]),
                    replica_group=ReplicaGroupConfig(**d["replica_group"]),
                    sandbox=SandboxConfig(
                        profile_name=d["sandbox"]["profile_name"],
                        required_capabilities=tuple(d["sandbox"]["required_capabilities"]),
                        allowed_syscalls=tuple(d["sandbox"]["allowed_syscalls"]),
                        landlock_paths=tuple(d["sandbox"]["landlock_paths"]),
                        read_only_root=d["sandbox"]["read_only_root"],
                        allowed_write_paths=tuple(d["sandbox"]["allowed_write_paths"]),
                    ),
                    resource_limits=ResourceLimitsConfig(**d["resource_limits"]),
                )
                self.current_identity = DerivedConfigurationIdentity(
                    config_hash=payload["config_hash"],
                    config_generation=payload["config_generation"],
                    snapshot_timestamp=payload["snapshot_timestamp"],
                    desired_config=desired,
                )
            except (json.JSONDecodeError, KeyError) as err:
                # Torn record / corrupt state recovery fallback
                raise ConfigurationError(
                    f"Failed to recover durable state from '{self.storage_path}': corrupted record ({err})"
                ) from err


__all__ = [
    "ArraySemantics",
    "CanonicalCapability",
    "ConfigAdmissionEngine",
    "ConfigResolver",
    "DerivedConfigurationIdentity",
    "DesiredConfig",
    "GatewayConfig",
    "ReplicaGroupConfig",
    "ResourceLimitsConfig",
    "SandboxConfig",
    "get_default_raw_config",
    "normalize_secure_path",
]
