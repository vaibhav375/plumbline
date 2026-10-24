import httpx

from plumbline import db


def test_synthetic_history_runs_are_skipped():
    real = {"findings": [{"id": "f1"}], "needs_human": []}

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path == "/check_runs":
            return httpx.Response(
                200,
                json=[
                    {"id": "r1", "version_id": "v1", "report_json": real},
                    {"id": "r2", "version_id": "v2", "report_json": {"synthetic": True}},
                ],
            )
        assert "r2" not in req.url.params["run_id"]
        return httpx.Response(
            200,
            json=[
                {"id": "rec1", "run_id": "r1", "payload_json": {"group": "findings", "id": "f1"}}
            ],
        )

    with httpx.Client(base_url="http://x", transport=httpx.MockTransport(handler)) as c:
        out = db._reports_with_ids(c, ["v1", "v2"])
    assert list(out) == ["v1"]
    assert out["v1"]["findings"][0]["record_id"] == "rec1"


def test_titles_are_cut_at_a_word_boundary():
    from plumbline.db import clip_title

    long = "Meet the NEW Aurelle Vitamin-C serum!!! 100% natural, eco-friendly and clinically proven to fade dark spots by 60% in just 2 weeks."
    t = clip_title(long)
    assert len(t) <= 120 and t.endswith("by 60% in…") and "in ju" not in t
    assert clip_title("Short post title ") == "Short post title"
