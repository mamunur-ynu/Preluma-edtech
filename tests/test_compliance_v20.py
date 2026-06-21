from analytics_core import mean, population_variance, frequency_table, readiness_summary
from algorithms_core import merge_sort_records, add_normalized_name, linear_search_by_name, collect_binary_search_matches
from storage_core import FIELDNAMES
from teacher import teacher_analytics, search_student

def test_pure_python_mean_variance():
    values=[80.0,90.0,100.0]
    assert mean(values)==90.0
    assert round(population_variance(values),2)==66.67

def test_frequency_summary():
    rows=[{'Student':'A','Readiness':80.0,'Weak Skill':'Definition'},{'Student':'B','Readiness':90.0,'Weak Skill':'Definition'},{'Student':'C','Readiness':70.0,'Weak Skill':'Application'}]
    freq=frequency_table(rows,'Weak Skill'); summary=readiness_summary(rows)
    assert summary['class_average']==80.0
    assert summary['unique_weak_skills']==2
    assert any(row['Weak Skill']=='Definition' and row['Count']==2 for row in freq)

def test_merge_sort_and_binary_search():
    rows=[{'Student':'Zhou','Readiness':92.0},{'Student':'Mamunur','Readiness':95.0},{'Student':'Fahim','Readiness':76.0}]
    ranked=merge_sort_records(rows,'Readiness',True)
    assert ranked[0]['Student']=='Mamunur'
    named=merge_sort_records(add_normalized_name(rows),'student_name_norm',False)
    assert linear_search_by_name(named,'mamunur')[0]['Student']=='Mamunur'
    assert collect_binary_search_matches(named,'mamunur')[0]['Student']=='Mamunur'

def test_teacher_analytics_search_contract():
    rows=[{'Student':'Mamunur','Topic':'Python','Readiness':95.0,'Weak Skill':'None'},{'Student':'Fahim','Topic':'Python','Readiness':76.0,'Weak Skill':'Application'}]
    analytics=teacher_analytics(rows); result=search_student(rows,'Mamunur')
    assert analytics['summary']['students_tracked']==2
    assert analytics['sorted_by_readiness'][0]['Student']=='Mamunur'
    assert result['binary_result'][0]['Student']=='Mamunur'

def test_storage_schema_contains_required_fields():
    assert 'Student' in FIELDNAMES and 'Readiness' in FIELDNAMES and 'Created At' in FIELDNAMES
