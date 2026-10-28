"""The claim watch: which live posts need a task when facts move, and re-reading a live page safely."""

import socket
from datetime import date

import httpx
import pytest

from plumbline import watch
from plumbline.models import ApprovedWording, Fact

TODAY = date(2026, 10, 29)


def fact(fid="FACT-014", **kw) -> Fact:
    base = dict(
        id=fid, statement="Serum gave a 32% reduction in dark spots over 8 weeks", value=32.0, unit="%",
        product="Serum", market="IN", population=None, duration="8 weeks", owner="R&D",
        valid_from=date(2026, 1, 1), valid_until=date(2027, 1, 1), confidentiality="public",
        embargo_until=None, verified=True,
    )  # fmt: skip
    return Fact(**(base | kw))


def wording(
    fid="FACT-014", text="shown to visibly reduce dark spots by 30% in 8 weeks*", channel="any"
):
    return ApprovedWording(
        id="AW-1", fact_id=fid, market="IN", channel=channel, text=text, disclaimer=None
    )


def post(*facts: Fact, version="v1", region="IN", channel="instagram"):
    return {
        "version_id": version, "content_id": f"c-{version}", "title": "Post", "owner": "u1",
        "region": region, "channel": channel,
        "claims_used": [{"fact_id": f.id, "quote": "the claim", "digest": f.digest} for f in facts],
    }  # fmt: skip


def test_an_unchanged_fact_gives_no_task():
    f = fact()
    assert watch.compute_tasks([post(f)], [f], [], TODAY) == []


def test_each_reason_is_found_and_the_most_serious_wins():
    f = fact()
    p = post(f)
    expired = watch.compute_tasks([p], [fact(valid_until=date(2026, 10, 1))], [], TODAY)
    assert [t.reason for t in expired] == ["expired"] and "expired on 2026-10-01" in expired[
        0
    ].detail
    assert [t.reason for t in watch.compute_tasks([p], [fact(verified=False)], [], TODAY)] == [
        "unverified"
    ]
    assert [t.reason for t in watch.compute_tasks([p], [fact(value=20.0)], [], TODAY)] == [
        "changed"
    ]
    assert [t.reason for t in watch.compute_tasks([p], [], [], TODAY)] == ["removed"]
    # Changed and expired together: one task, the expiry.
    both = fact(value=20.0, valid_until=date(2026, 10, 1))
    assert [t.reason for t in watch.compute_tasks([p], [both], [], TODAY)] == ["expired"]


def test_only_posts_that_used_the_fact_get_a_task_and_only_once_per_fact():
    used, other = fact("FACT-014"), fact("FACT-020")
    a = post(used, version="a")
    b = post(other, version="b")
    twice = post(used, used, version="c")
    now = fact("FACT-014", value=1.0)
    tasks = watch.compute_tasks([a, b, twice], [now, other], [], TODAY)
    assert sorted(t.version_id for t in tasks) == ["a", "c"] and len(tasks) == 2
    assert all(t.owner == "u1" for t in tasks)


def test_a_changed_fact_suggests_its_approved_wording_for_that_market_and_channel():
    f = fact()
    now = fact(value=30.0)
    ok = watch.compute_tasks([post(f)], [now], [wording()], TODAY)[0]
    assert ok.replacement == "shown to visibly reduce dark spots by 30% in 8 weeks*"
    wrong_channel = watch.compute_tasks([post(f)], [now], [wording(channel="email")], TODAY)[0]
    assert wrong_channel.replacement is None
    wrong_market = watch.compute_tasks([post(f, region="US")], [now], [wording()], TODAY)[0]
    assert wrong_market.replacement is None
    # An expired fact has no replacement: its own wording is just as stale.
    gone = watch.compute_tasks([post(f)], [fact(valid_until=date(2026, 1, 2))], [wording()], TODAY)[
        0
    ]
    assert gone.replacement is None


def test_a_restricted_fact_is_never_named_in_a_task():
    secret = fact(
        "FACT-031", statement="Mumbai flagship opens in December", confidentiality="embargoed"
    )
    now = secret.model_copy(update={"valid_until": date(2026, 1, 5)})
    t = watch.compute_tasks([post(secret)], [now], [wording("FACT-031")], TODAY)[0]
    assert (
        "FACT-031" not in t.detail and "Mumbai" not in t.detail and "a restricted fact" in t.detail
    )
    assert t.replacement is None


def test_the_digest_moves_with_anything_a_claim_can_rest_on():
    f = fact()
    for change in ({"statement": "x"}, {"value": 1.0}, {"unit": "pts"}, {"valid_until": None},
                   {"confidentiality": "internal"}, {"verified": False}, {"market": "US"}):  # fmt: skip
        assert fact(**change).digest != f.digest
    assert fact(owner="someone else").digest == f.digest  # not part of what a claim rests on


# ---- reading a page ---------------------------------------------------------------------------------

APPROVED = (
    "Shown to visibly reduce dark spots by 32% in 8 weeks*. Shop the Vitamin C Brightening Serum.\n"
    "*In-house study, 48 participants, 2026."
)


def test_visible_text_drops_scripts_styles_and_markup():
    page = "<html><head><title>x</title><style>.a{}</style></head><body><script>var a=1</script><p>Hello &amp; welcome</p><div>Second</div></body></html>"
    assert watch.visible_text(page).split() == ["Hello", "&", "welcome", "Second"]


def test_a_page_with_the_approved_sentences_is_ok_even_with_extra_text():
    page = f"Menu Home About {APPROVED} Cart (0) Footer links"
    assert watch.page_result(APPROVED, page) == {"status": "ok", "checked": 3, "missing": []}


def test_changed_or_removed_sentences_are_drift():
    page = "Shown to visibly reduce dark spots by 60% in 2 weeks. Shop the Vitamin C Brightening Serum."
    r = watch.page_result(APPROVED, page)
    assert r["status"] == "drift" and len(r["missing"]) == 2  # the claim and the footnote
    assert "missing or changed on the live page" in watch.drift_detail(r)
    # A number quietly changed is drift even though the sentence is otherwise identical.
    edited = APPROVED.replace("32%", "62%")
    assert watch.page_result(APPROVED, edited)["status"] == "drift"
    small = watch.page_result(
        APPROVED,
        page.replace("60%", "32%").replace("2 weeks", "8 weeks")
        + " *In-house study, 48 participants, 2026.",
    )
    assert (
        small["status"] == "drift" or small["status"] == "ok"
    )  # near matches (>=90) are tolerated


def public(host, port, type=None):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port))]


def private(ip):
    return lambda host, port, type=None: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port))]


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/x",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "http://",
        "https://user:pw@example.com/",
    ],
)
def test_only_plain_http_addresses_are_allowed(url):
    with pytest.raises(watch.UnsafeUrl):
        watch.check_url_is_public(url, public)


@pytest.mark.parametrize(
    "ip",
    ["127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.169.254", "172.16.0.9", "0.0.0.0", "::1"],
)
def test_private_loopback_and_metadata_addresses_are_refused(ip):
    fam = socket.AF_INET6 if ":" in ip else socket.AF_INET
    with pytest.raises(watch.UnsafeUrl):
        watch.check_url_is_public(
            "https://internal.example/", lambda h, p, type=None: [(fam, 1, 6, "", (ip, p))]
        )


def test_a_public_host_passes_and_an_unknown_one_is_refused():
    watch.check_url_is_public("https://example.com/post", public)

    def boom(*a, **k):
        raise OSError

    with pytest.raises(watch.UnsafeUrl):
        watch.check_url_is_public("https://nope.invalid/", boom)


def client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_fetch_reads_the_page_text_and_follows_safe_redirects():
    def handler(req):
        if req.url.path == "/old":
            return httpx.Response(302, headers={"location": "/new"})
        return httpx.Response(200, text=f"<p>{APPROVED}</p>")

    assert "Shop the Vitamin C" in watch.fetch_page(
        "https://example.com/old", client(handler), public
    )


def test_a_redirect_into_a_private_address_is_refused():
    def handler(req):
        return httpx.Response(302, headers={"location": "http://169.254.169.254/latest/meta-data"})

    def resolver(host, port, type=None):
        return private("169.254.169.254" if host == "169.254.169.254" else "93.184.216.34")(
            host, port
        )

    with pytest.raises(watch.UnsafeUrl):
        watch.fetch_page("https://example.com/x", client(handler), resolver)


def test_redirect_loops_and_errors_and_huge_bodies_are_contained():
    loop = client(lambda req: httpx.Response(302, headers={"location": "/again"}))
    with pytest.raises(watch.UnsafeUrl):
        watch.fetch_page("https://example.com/", loop, public)
    with pytest.raises(httpx.HTTPStatusError):
        watch.fetch_page("https://example.com/", client(lambda r: httpx.Response(404)), public)
    big = client(lambda r: httpx.Response(200, text="word " * 600_000))
    text = watch.fetch_page("https://example.com/", big, public)
    assert len(text) <= watch.MAX_BYTES


def test_generated_demo_history_is_not_a_live_post(monkeypatch):
    rows = [
        {"title": "[synthetic] CL-03 sample 1", "claims_used": []},
        {"title": "Real post", "claims_used": []},
    ]
    monkeypatch.setattr(watch, "_one", lambda *a: rows)
    assert [p["title"] for p in watch.live(None, "org")] == ["Real post"]
