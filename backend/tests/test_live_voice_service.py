from app.services.live_voice_service import LiveVoiceService


def test_live_transcript_chunks_are_joined_without_repeating_the_overlap():
    parts = []
    LiveVoiceService._append_transcript(parts, "Hello")
    LiveVoiceService._append_transcript(parts, "Hello there")
    LiveVoiceService._append_transcript(parts, "there friend")

    assert "".join(parts) == "Hello there friend"


def test_live_transcript_word_tokens_preserve_spaces_without_squishing():
    parts = []
    chunks = [
        "I've",
        "captured",
        "another",
        "frame",
        "from",
        "your",
        "webcam",
        "and",
        "displayed",
        "the",
        "last",
        "one",
        "I",
        "took",
        "on",
        "the",
        "display",
        "for",
        "you.",
        "There",
        "might",
        "be",
        "a",
        "slight",
        "delay.",
        "Do",
        "you",
        "see",
        "it",
        "okay?",
    ]
    for chunk in chunks:
        LiveVoiceService._append_transcript(parts, chunk)

    assert "".join(parts) == (
        "I've captured another frame from your webcam and displayed the last one "
        "I took on the display for you. There might be a slight delay. Do you see it okay?"
    )


def test_live_transcript_tokens_with_leading_spaces():
    parts = []
    chunks = ["Hello", " there", " my", " friend,", " welcome!"]
    for chunk in chunks:
        LiveVoiceService._append_transcript(parts, chunk)

    assert "".join(parts) == "Hello there my friend, welcome!"
