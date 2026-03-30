from app.retrieval.merge import merge_sources
from app.schemas import SourceDocument


def test_merge_sources_deduplicates_same_content() -> None:
    source_a = SourceDocument(
        title="Alpha",
        content="Same body",
        source_type="web",
        url_or_path="https://a.example",
        confidence=0.9,
    )
    source_b = SourceDocument(
        title="Alpha",
        content="Same body",
        source_type="local_kb",
        url_or_path="https://a.example",
        confidence=0.7,
    )

    merged = merge_sources([source_a], [source_b])
    assert len(merged) == 1
