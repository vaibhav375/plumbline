from plumbline.config import Settings

REQUIRED = {
    "SUPABASE_URL": "https://x.supabase.co",
    "SUPABASE_ANON_KEY": "anon",
}


def test_settings_defaults(monkeypatch):
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("LLM_CHAIN", raising=False)
    s = Settings(_env_file=None)
    assert s.max_upload_mb == 10
    assert s.llm_chain == ["groq", "gemini"]
    assert s.match_threshold == 0.72


def test_llm_chain_from_env(monkeypatch):
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)
    monkeypatch.setenv("LLM_CHAIN", '["ollama"]')
    assert Settings(_env_file=None).llm_chain == ["ollama"]
