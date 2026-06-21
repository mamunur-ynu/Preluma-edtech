from topics import validate_topics

def test_topic_registry_validates_cleanly():
    assert validate_topics() == []
