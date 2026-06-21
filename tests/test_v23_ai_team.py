from pathlib import Path
from llm import detect_topic_from_question


def test_question_topic_overrides_old_context():
    assert detect_topic_from_question('about machine learning', 'Variance') == 'Machine Learning'
    assert detect_topic_from_question('Explain quantum mechanics simply', 'Statistics') == 'Quantum Mechanics'


def test_team_photo_is_packaged():
    image = Path('assets/team_preluma.jpg')
    assert image.exists()
    assert image.stat().st_size > 100_000


def test_six_provider_ready_architecture():
    text = Path('llm.py').read_text(encoding='utf-8')
    for key in [
        'OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'GEMINI_API_KEY',
        'GROQ_API_KEY', 'OPENROUTER_API_KEY', 'TOGETHER_API_KEY',
    ]:
        assert key in text
