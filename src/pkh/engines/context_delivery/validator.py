"""Context validator."""

from __future__ import annotations

from pkh.engines.context_delivery.models import ContextPackage


class ValidationResult:
    def __init__(self, valid: bool, warnings: list[str], token_count: int):
        self.valid = valid
        self.warnings = warnings
        self.token_count = token_count


class ContextValidator:
    def validate(self, package: ContextPackage, max_tokens: int = 128000) -> ValidationResult:
        warnings: list[str] = list(package.warnings)

        # token check — unified with compressor: max(1, len//4)
        token_count = sum(max(1, len(c.content) // 4) for c in package.knowledge)
        if token_count > max_tokens:
            warnings.append(f"Context exceeds model limit by {token_count - max_tokens} tokens")

        # traceability
        missing = [c for c in package.knowledge if not c.sources]
        if missing:
            warnings.append(f"{len(missing)} chunks missing source references")

        # lifecycle
        deprecated = [
            c for c in package.knowledge if str(c.lifecycle_state) in ("DEPRECATED", "ARCHIVED")
        ]
        if deprecated:
            warnings.append(f"{len(deprecated)} deprecated chunks included")

        # confidence
        low_conf = [c for c in package.knowledge if c.confidence < 0.5]
        if low_conf:
            warnings.append(f"{len(low_conf)} low-confidence chunks included")

        return ValidationResult(
            valid=len(warnings) == 0, warnings=warnings, token_count=token_count
        )
