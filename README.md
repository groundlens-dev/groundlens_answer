<div align="center">

![GroundLens](https://raw.githubusercontent.com/groundlens-dev/groundlens/main/docs/assets/groundlens_header.png)

# GroundLens Answer

**A Guardrails validator that checks the figures in an LLM answer against the passages it was written from.**

Exact comparison, no model, no network call.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)
[![GroundLens](https://img.shields.io/pypi/v/groundlens?label=groundlens&color=1a4fd6)](https://pypi.org/project/groundlens/)

</div>

<br>

A RAG answer can read well and still carry the wrong number: €42.1 million where the report says €41.2 million, or the right amount taken from the wrong company. A model asked to judge the answer will often miss it, and will not give the same verdict twice. This validator reads the figures as values and compares them with the passages, so the same answer always gets the same decision, with the reason.

## What it catches

The first three rows use two passages, each tagged with its company: *"In 2024, ACME's revenue reached €41.2 million, up from €38.0 million in 2023."* (ACME) and *"Globex's revenue was €52.7 million."* (Globex).

| The answer says | Result | Why |
|---|---|---|
| ACME's revenue was €42.1 million in 2024. | ❌ fails | €42.1 million is in no passage; the nearest is €41.2 million. |
| Revenue rose from €38.0 million to €41.2 million, up 8.4%. | ✅ passes | 8.4% is in no passage, but it is recomputed from the two amounts. |
| ACME's revenue was €52.7 million. *(scope: ACME)* | ❌ fails | The figure is real, but it comes from Globex's passage. |
| Revenue was €2.5bn. *(passage: 2,500 million euros)* | ✅ passes | Scales, currencies and units are compared as quantities. |

It checks figures. Sentences without figures, tone and safety are for other validators, and it does not check facts against the world, only against the passages you give it.

## Install

```bash
pip install git+https://github.com/groundlens-dev/groundlens_answer
```

Python 3.10+. It installs [GroundLens](https://github.com/groundlens-dev/groundlens), which ships prebuilt wheels for Linux, macOS and Windows. No API key is needed.

## Quickstart

```python
from guardrails import Guard
from validator import GroundLensAnswer

guard = Guard().use(GroundLensAnswer(on_fail="exception"))

passages = ["In 2024, ACME's revenue reached €41.2 million, up from €38.0 million in 2023."]

guard.validate(
    "Revenue rose from €38.0 million to €41.2 million, up 8.4%.",
    metadata={"passages": passages},
)  # passes

guard.validate(
    "ACME's revenue was €42.1 million in 2024.",
    metadata={"passages": passages},
)  # raises: GroundLens decided FAIL: c2: groundlens.numeric contradicted: €42.1 million not in sources; nearest 41200000 EUR in ctx-0 ...
```

The passages go in `metadata`, next to the answer, so the validator sees exactly what the model saw.

## Check the right company, and the right kind of figure

Give each passage an id and its provenance, and say what the answer must be about:

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
)  # raises: €52.7 million comes from Globex's passage
```

With the question, an answer that gives an amount when a percentage was asked goes to review.

## How it decides

GroundLens decides `PASS`, `REVIEW` or `FAIL` under a policy:

- **FAIL** when a figure contradicts the passages, or comes from a passage outside the scope.
- **REVIEW** when a check could not decide, for example a required scope the passages do not state. A check that could not run is `REVIEW`, never `PASS`.
- **PASS** otherwise.

The validator fails on `FAIL` and `REVIEW`. To let answers that need review through, use `fail_on=["FAIL"]`. The decision, the record id and the policy are in the `metadata` of the validation result.

## Keep a signed record of every decision

```python
guard = Guard().use(
    GroundLensAnswer(
        policy="eu_ai_act_high_risk_v1",
        records_dir="records/",
        on_fail="exception",
    )
)
```

Each validation appends a record to `records/records.jsonl`: the decision, the evidence, the policy and a hash of the input, chained to the record before and signed. Anyone can check the whole log offline:

```bash
groundlens record verify records/records.jsonl
# ok  2 records, chain intact, all signatures verify
```

The `eu_ai_act_high_risk_v1` policy maps decisions to Articles 12, 14 and 15 of the EU AI Act. It produces evidence for those controls; it does not make a system compliant on its own.

## Validator card

| Developed by | [GroundLens](https://groundlens.dev) |
| --- | --- |
| Date of development | Oct 15, 2026 |
| Validator type | Factuality, RAG |
| License | Apache 2 |
| Input/Output | Output |
| Dependencies | guardrails-ai>=0.5.0, groundlens>=6.0.1 |
| Foundation model access keys | None |

## API reference

**`__init__(self, policy=None, records_dir=None, fail_on=("FAIL", "REVIEW"), locale="und", on_fail="noop")`**
<ul>
Initializes a new instance of the GroundLensAnswer class.

**Parameters**
- **`policy`** *(str)*: A shipped GroundLens policy, `groundlens_default_v1` (default) or `eu_ai_act_high_risk_v1`, or the path of a policy YAML file.
- **`records_dir`** *(str)*: A directory where every decision is kept as a signed, hash-chained record. When omitted, records are signed but not stored.
- **`fail_on`** *(Iterable[str])*: The GroundLens decisions that make the validator fail. Default `("FAIL", "REVIEW")`; use `("FAIL",)` to let answers that need review through.
- **`locale`** *(str)*: The locale the figures are written in, e.g. `es` or `de` for `1.234,5`. Default `und`, which reads both conventions when they are unambiguous.
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
