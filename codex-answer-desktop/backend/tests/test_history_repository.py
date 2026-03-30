from app.schemas import HistoryItem, TokenUsage
from app.storage.history import HistoryRepository


def test_history_repository_updates_and_deletes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.config.settings.history_file", tmp_path / "history.json")
    repo = HistoryRepository()
    item = HistoryItem(
        run_id="run-1",
        query="hello",
        created_at="2026-03-31T00:00:00+08:00",
        final_answer="answer",
        source_count=1,
        citations_present=True,
        model="gpt-5",
        token_usage=TokenUsage(total_tokens=12),
    )

    repo.append(item)
    updated = repo.update("run-1", {"translated_answer": "翻译后"})

    assert updated.translated_answer == "翻译后"

    repo.delete("run-1")
    assert repo.list_items() == []
