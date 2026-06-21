from wiki_fetcher import extract_keywords, simplify_text, smart_answer_from_pack

def test_keyword_extraction():
    words = extract_keywords("Machine learning learns patterns from data and data examples.", limit=3)
    assert "data" in words

def test_smart_answer_from_pack_local():
    pack = {
        "title": "Test Topic",
        "definition": "Test Topic is a simple topic used for checking.",
        "simple": "It is simple.",
        "facts": ["It has facts."],
        "misconceptions": ["Do not memorize only."],
        "class_questions": ["What is it?"],
        "applications": {"testing": "Used for testing."},
    }
    ans = smart_answer_from_pack(pack, "What is Test Topic?")
    assert ans["answer"]
    assert ans["simple"]
