# to run these, run
# make test

import groundlens as gl
import pytest
from guardrails import Guard

from validator import GroundLensAnswer

PASSAGES = ["In 2024, ACME's revenue reached €41.2 million, up from €38.0 million in 2023."]


def guard(**kwargs):
    return Guard().use(GroundLensAnswer(on_fail="exception", **kwargs))


def test_pass():
    answer = "ACME's revenue was €41.2 million in 2024."
    result = guard().validate(answer, metadata={"passages": PASSAGES})

    assert result.validation_passed is True
    assert result.validated_output == answer


def test_fail_on_a_wrong_figure():
    with pytest.raises(Exception) as exc_info:
        guard().validate("ACME's revenue was €42.1 million in 2024.", metadata={"passages": PASSAGES})

    message = str(exc_info.value)
    assert "GroundLens decided FAIL" in message
    assert "€42.1 million not in sources" in message


def test_pass_on_a_computed_figure():
    # 8.4% is in no passage: it is recomputed from the two supported amounts.
    answer = "Revenue rose from €38.0 million to €41.2 million, up 8.4%."
    result = guard().validate(answer, metadata={"passages": PASSAGES})

    assert result.validation_passed is True


def test_review_can_pass():
    # A required scope key that the passages do not carry goes to REVIEW.
    answer = "Revenue was €41.2 million."
    metadata = {"passages": PASSAGES, "scope": {"entity": "ACME"}}

    with pytest.raises(Exception) as exc_info:
        guard().validate(answer, metadata=metadata)
    assert "GroundLens decided REVIEW" in str(exc_info.value)

    result = guard(fail_on=["FAIL"]).validate(answer, metadata=metadata)
    assert result.validation_passed is True


def test_records_are_kept(tmp_path):
    guard(records_dir=str(tmp_path)).validate("ACME's revenue was €41.2 million in 2024.", metadata={"passages": PASSAGES})

    lines = (tmp_path / "records.jsonl").read_text().splitlines()
    assert len(lines) == 1
    assert gl.Record.from_json(lines[0]).decision == "PASS"


def test_passages_are_required():
    with pytest.raises(Exception, match="passages"):
        guard().validate("Revenue was €41.2 million.", metadata={})
