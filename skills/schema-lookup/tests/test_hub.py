import schema
from hub import hub_passages, hub_rows


def test_exact_row_for_dotted_field(fields):
    rows = hub_rows("Area", "BGAGC", fields)
    assert rows and rows[0].match == "exact"
    assert any(r.tag.startswith("V") for r in rows)


def test_untagged_table_rows_carry_no_tag(fields):
    glance = [r for r in hub_rows("Area", "BGAGC", fields) if r.section == "Every study at a glance"]
    assert glance and all(r.tag == "" for r in glance)


def test_other_objects_dotted_row_is_not_returned(fields):
    rows = hub_rows("SuperArea", "BGAGC", fields)
    assert [r.tag[:1] for r in rows] == ["S"]


def test_decoy_text_reaches_the_reader(fields):
    rows = hub_rows("CTG_Options", "CTG_ReportMonitoredAreas", fields)
    assert any("decoy" in r.text for r in rows)


def test_no_exact_claim_for_same_name_on_another_object(fields):
    for obj, fld in [("Contingency", "GenMW"), ("Load", "GenCostCurvePoints"), ("Gen", "BusPUVolt")]:
        assert schema.find_field(obj, fld, fields) is not None, (obj, fld)
        assert not [r for r in hub_rows(obj, fld, fields) if r.match == "exact"], (obj, fld)


def test_field_absent_from_hub_returns_nothing(fields):
    assert hub_rows("Substation", "NERCCIP14AggWeight", fields) == []


def test_field_absent_from_export_returns_nothing(fields):
    assert hub_rows("OPF_Options", "SCOPFMaxInnerLoopItr", fields) == []


def test_passages_answer_the_inner_loop_question():
    top = hub_passages(schema.split_words("SCOPFMaxInnerLoopItr"))
    assert top and "OPF_MaxLPIterations" in top[0]
