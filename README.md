# Overview

| Developed by | GroundLens |
| --- | --- |
| Date of development | Oct 15, 2026 |
| Validator type | Factuality, RAG |
| Blog | https://groundlens.dev |
| License | Apache 2 |
| Input/Output | Output |

## Description

### Intended Use

This validator checks that the figures in an LLM answer are supported by the passages the answer was written from: amounts, rates, percentages, dates and units. It is meant for RAG answers where a wrong figure is expensive, such as finance, insurance, legal and compliance assistants.

It runs [GroundLens](https://github.com/groundlens-dev/groundlens), which compares figures as exact values, with no model and no network call:

- **A wrong figure fails.** The answer says €42.1 million where the passage says €41.2 million.
- **Arithmetic is recomputed.** A sum, a difference, a ratio or a percentage change that no passage contains is recomputed from the answer's own supported figures, so a correct "up 8.4%" passes.
- **Locales and scales are understood.** `1.234,5` and `1,234.5`, "€2.5bn" and "2,500 million", `1,2 km` and `1200 m`.
- **Optional scope.** With `scope={"entity": "ACME"}` and passages that state their provenance, a real figure taken from the wrong company, contract or year fails.
- **Optional intent.** With the question, an answer that gives an amount when a percentage was asked goes to review.

GroundLens decides `PASS`, `REVIEW` or `FAIL` under a policy. The validator fails on `FAIL` and `REVIEW` by default; a check that could not run is `REVIEW`, never `PASS`. Each decision can also be kept as a signed, hash-chained record that anyone can verify offline.

The validator checks figures against the given passages. It does not judge sentences without figures, and it does not check facts against the world.

### Requirements

* Dependencies:
    - guardrails-ai>=0.5.0
    - groundlens>=6.0.1 (Python 3.10+, prebuilt wheels for Linux, macOS and Windows)

* Foundation model access keys:
    - None. No model is called.

## Installation

```bash
$ guardrails hub install hub://groundlens/groundlens_answer
```

## Usage Examples

### Validating string output via Python

The passages the answer was written from go in `metadata`.

```python
# Import Guard and Validator
from guardrails.hub import GroundLensAnswer
from guardrails import Guard

# Setup Guard
guard = Guard().use(GroundLensAnswer(on_fail="exception"))

passages = ["In 2024, ACME's revenue reached €41.2 million, up from €38.0 million in 2023."]

guard.validate(
    "Revenue rose from €38.0 million to €41.2 million, up 8.4%.",
    metadata={"passages": passages},
)  # Validator passes: both amounts are in the passage, and 8.4% is recomputed from them

guard.validate(
    "ACME's revenue was €42.1 million in 2024.",
    metadata={"passages": passages},
)  # Validator fails: GroundLens decided FAIL: c2: groundlens.numeric contradicted: €42.1 million not in sources; nearest 41200000 EUR in ctx-0 ...
```

### Keeping a signed record of every decision

```python
guard = Guard().use(
    GroundLensAnswer(
        policy="eu_ai_act_high_risk_v1",
        records_dir="records/",
        on_fail="exception",
    )
)
```

Each validation appends a signed record to `records/records.jsonl`, chained to the one before. `groundlens record verify records/records.jsonl` checks the chain and the signatures. The `eu_ai_act_high_risk_v1` policy maps its decisions to Articles 12, 14 and 15 of the EU AI Act.

### Checking scope and intent

```python
passages = [
    ("q4-acme", "ACME's Q4 revenue was €41.2 million.", {"entity": "ACME"}),
    ("q4-globex", "Globex's Q4 revenue was €52.7 million.", {"entity": "Globex"}),
]

guard.validate(
    "Q4 revenue was €52.7 million.",
    metadata={
        "passages": passages,
        "question": "What was ACME's Q4 revenue in euros?",
        "scope": {"entity": "ACME"},
    },
)  # Validator fails: €52.7 million comes from Globex's passage
```

# API Reference

**`__init__(self, policy=None, records_dir=None, fail_on=("FAIL", "REVIEW"), locale="und", on_fail="noop")`**
<ul>
Initializes a new instance of the GroundLensAnswer class.

**Parameters**
- **`policy`** *(str)*: A shipped GroundLens policy, `groundlens_default_v1` (default) or `eu_ai_act_high_risk_v1`, or the path of a policy YAML file.
- **`records_dir`** *(str)*: A directory where every decision is kept as a signed, hash-chained record. When omitted, records are signed but not stored.
- **`fail_on`** *(Iterable[str])*: The GroundLens decisions that make the validator fail. Default `("FAIL", "REVIEW")`; use `("FAIL",)` to let answers that need review through.
- **`locale`** *(str)*: The locale the figures are written in, e.g. `es-ES` for `1.234,5`. Default `und`, which reads both conventions when they are unambiguous.
- **`on_fail`** *(str, Callable)*: The policy to enact when a validator fails. If `str`, must be one of `reask`, `fix`, `filter`, `refrain`, `noop`, `exception` or `fix_reask`. Otherwise, must be a function that is called when the validator fails.
</ul>
<br/>

**`validate(self, value, metadata) -> ValidationResult`**
<ul>
Validates the given `value` using the rules defined in this validator, relying on the `metadata` provided to customize the validation process. This method is automatically invoked by `guard.parse(...)`, ensuring the validation logic is applied to the input data.

Note:

1. This method should not be called directly by the user. Instead, invoke `guard.parse(...)` where this method will be called internally for each associated Validator.
2. When invoking `guard.parse(...)`, ensure to pass the appropriate `metadata` dictionary that includes keys and values required by this validator. If `guard` is associated with multiple validators, combine all necessary metadata into a single dictionary.

**Parameters**
- **`value`** *(Any)*: The answer to validate.
- **`metadata`** *(dict)*: A dictionary containing metadata required for validation. Keys and values must match the expectations of this validator.


    | Key | Type | Description | Default |
    | --- | --- | --- | --- |
    | `passages` | list | The texts the answer was written from: strings, or `(id, text, provenance)` tuples whose provenance is a dict such as `{"entity": "ACME"}`. | Required |
    | `question` | str | The question asked. Turns on the intent check. | None |
    | `scope` | dict | What the answer must be about, e.g. `{"entity": "ACME"}`. Turns on the scope check. | None |

The `metadata` of the result carries the GroundLens `decision`, the `record_id`, the `record_hash` and the `policy_id`.
</ul>
