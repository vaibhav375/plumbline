from plumbline.rules.load import load_rules_csv

HEADER = (
    "id,title,category,cls,check_type,params,severity,tier,maturity,"
    "examples_good,examples_bad,source_ref,owner_function\n"
)
GOOD = (
    'TN-02,Max one !,tone,A,count,"{""regex"": ""!"", ""max"": 1}",'
    "minor,brand,advisory,a|b,,GL,brand\n"
)


def test_csv_good_row():
    rules, errors = load_rules_csv(HEADER + GOOD)
    assert errors == []
    assert rules[0].params == {"regex": "!", "max": 1} and rules[0].examples_good == ["a", "b"]


def test_csv_bad_row_reported():
    bad = "X-1,Bad,tone,A,foo,{},minor,brand,advisory,,,GL,brand\n"
    rules, errors = load_rules_csv(HEADER + GOOD + bad)
    assert [r.id for r in rules] == ["TN-02"]
    assert len(errors) == 1 and "Row 3" in errors[0] and "check_type" in errors[0]


def test_csv_bad_json_and_duplicate_id():
    bad_json = "X-2,Bad,tone,A,pattern,{not json},minor,brand,advisory,,,GL,brand\n"
    rules, errors = load_rules_csv(HEADER + GOOD + bad_json + GOOD)
    assert any("Row 3" in e and "params" in e for e in errors)
    assert any("Row 4" in e and "duplicate" in e.lower() for e in errors)


def test_csv_missing_columns():
    rules, errors = load_rules_csv("id,title\nA,B\n")
    assert rules == [] and errors and "column" in errors[0].lower()
