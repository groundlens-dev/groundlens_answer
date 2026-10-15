from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

import groundlens as gl
from guardrails.validator_base import (
    FailResult,
    PassResult,
    ValidationResult,
    Validator,
    register_validator,
)


@register_validator(name="groundlens/groundlens_answer", data_type="string")
class GroundLensAnswer(Validator):
    """Validates that the figures in an LLM answer are supported by the passages it was written from.

    **Key Properties**

    | Property                      | Description                       |
    | ----------------------------- | --------------------------------- |
    | Name for `format` attribute   | `groundlens/groundlens_answer`      |
    | Supported data types          | `string`                          |
    | Programmatic fix              | None                              |

    GroundLens checks amounts, rates, percentages, dates and units as exact
    values, recomputes sums, ratios and percentage changes from the figures
    the passages support, and, when asked, checks that a figure comes from the
    right company, contract or year, and that the answer gives what the
    question asked. No model is called. The decision is `PASS`, `REVIEW` or
    `FAIL` under a GroundLens policy; the validator fails on the decisions in
    `fail_on`.

    Args:
        policy (str): A shipped GroundLens policy (`groundlens_default_v1`,
            `eu_ai_act_high_risk_v1`) or the path of a policy YAML file.
            Defaults to `groundlens_default_v1`.
        records_dir (str): A directory where every decision is kept as a
            signed, hash-chained record. When omitted, the records are signed
            but not stored.
        fail_on (Iterable[str]): The GroundLens decisions that make the
            validator fail. Defaults to `("FAIL", "REVIEW")`.
        locale (str): The locale the figures are written in, e.g. `es-ES`
            for `1.234,5`. Defaults to `und`, which reads both conventions
            when they are unambiguous.
    """

    def __init__(
        self,
        policy: str | None = None,
        records_dir: str | None = None,
        fail_on: Iterable[str] = ("FAIL", "REVIEW"),
        locale: str = "und",
        on_fail: Callable | None = None,
        **kwargs: Any,
    ):
        fail_on = tuple(fail_on)
        super().__init__(
            on_fail=on_fail,
            policy=policy,
            records_dir=records_dir,
            fail_on=fail_on,
            locale=locale,
            **kwargs,
        )
        unknown = set(fail_on) - {"FAIL", "REVIEW", "PASS"}
        if unknown:
            raise ValueError(f"fail_on takes FAIL, REVIEW or PASS, not {sorted(unknown)}")
        self._fail_on = frozenset(fail_on)
        sink = gl.sinks.jsonl(records_dir) if records_dir else None
        self._verifier = gl.Verifier(policy, sink=sink, locale=locale)

    def validate(self, value: Any, metadata: dict[str, Any] | None = None) -> ValidationResult:
        """Validates that the figures in `value` are supported by `metadata["passages"]`."""
        metadata = metadata or {}
        passages = metadata.get("passages")
        if not passages:
            raise ValueError('GroundLensAnswer needs metadata={"passages": [...]}: the texts the answer was written from')
        request = {
            "answer": str(value),
            "passages": passages,
            "question": metadata.get("question"),
            "scope": metadata.get("scope"),
        }
        if self._verifier.sink is not None:
            record = self._verifier.check(**request)
        else:
            record = self._verifier.seal(**request)

        result_metadata = {
            "decision": record.decision,
            "record_id": record.record_id,
            "record_hash": record.record_hash,
            "policy_id": record.policy_id,
        }
        if record.decision in self._fail_on:
            reasons = "; ".join(record.reasons) or "no reason given"
            return FailResult(
                error_message=f"GroundLens decided {record.decision}: {reasons}",
                metadata=result_metadata,
            )
        return PassResult(metadata=result_metadata)
