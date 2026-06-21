from analytics_core import mean, population_variance
from algorithms_core import merge_sort_records, add_normalized_name, collect_binary_search_matches
from teacher import teacher_analytics, search_student

def test_pure_python_statistics():
    assert mean([80, 90, 100]) == 90
    assert round(population_variance([80, 90, 100]), 2) == 66.67

def test_manual_sort_search():
    rows = [{"Student": "Zhou", "Readiness": 92}, {"Student": "Mamunur", "Readiness": 95}]
    ranked = merge_sort_records(rows, "Readiness", True)
    assert ranked[0]["Student"] == "Mamunur"
    named = merge_sort_records(add_normalized_name(rows), "student_name_norm", False)
    assert collect_binary_search_matches(named, "Mamunur")[0]["Student"] == "Mamunur"

def test_teacher_contract():
    rows = [{"Student": "Mamunur", "Readiness": 95, "Weak Skill": "None"}, {"Student": "Fahim", "Readiness": 76, "Weak Skill": "Application"}]
    analytics = teacher_analytics(rows)
    search = search_student(rows, "Mamunur")
    assert analytics["summary"]["class_average"] == 85.5
    assert search["binary_result"][0]["Student"] == "Mamunur"
