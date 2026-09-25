"""L1 tests for the REST client's read surface and typed API errors (#116).

The unmanaged-controls leg has to tell "the control is wrong" apart from "the
control could not be read", so every transport failure must arrive as an
:class:`ApiError` carrying a status the evaluator can branch on. No network
here: ``urlopen`` is stubbed for the single-GET reads, and the paginated helpers
run against a fake ``_send`` (#260) — one layer lower than the fake ``_request``
they used to use, because their stop condition is now the ``Link`` header, which
only exists at that layer.
"""

from __future__ import annotations

import urllib.error
import urllib.request

import pytest

from drift_layer.github_client import ApiError, RestGitHubClient, TruncatedResponseError
from tests.conftest import stub_response

ORG = "vig-os"

# A real `Link` header as GitHub sends it, captured from
# `GET /orgs/vig-os/repos?per_page=1` (14 pages of repositories).
NEXT_LINK = (
    '<https://api.github.com/organizations/244484004/repos?per_page=1&page=2>; rel="next", '
    '<https://api.github.com/organizations/244484004/repos?per_page=1&page=14>; rel="last"'
)
LAST_PAGE_LINK = (
    '<https://api.github.com/organizations/244484004/repos?per_page=1&page=13>; rel="prev", '
    '<https://api.github.com/organizations/244484004/repos?per_page=1&page=1>; rel="first"'
)

# What each helper asks for. The first page is a relative path carrying
# `per_page` and no `page`: since #260 the walk never composes a page number, it
# follows the absolute `rel="next"` target GitHub hands back (org paths come
# back rewritten to the org's numeric id, as captured here).
REPOS_PAGE_1 = f"/orgs/{ORG}/repos?per_page=100"
REPOS_PAGE_2 = "https://api.github.com/organizations/244484004/repos?per_page=100&page=2"
SECRETS_PAGE_1 = f"/orgs/{ORG}/actions/secrets?per_page=100"
SECRETS_PAGE_2 = (
    "https://api.github.com/organizations/244484004/actions/secrets?per_page=100&page=2"
)
SECRET_REPOS_PAGE_1 = f"/orgs/{ORG}/actions/secrets/COMMIT_APP_ID/repositories?per_page=100"
ISSUES_PAGE_1 = "/repos/vig-os/org-config/issues?state=open&labels=drift&per_page=100"
# The real cursor form the issues endpoint sends: an opaque `after=` target and
# NO `rel="last"` — a composed page number is not the same request.
ISSUES_PAGE_2 = (
    "https://api.github.com/repositories/1263724373/issues"
    "?state=open&labels=drift&per_page=100&page=2&after=Y3Vyc29yOnYyOpLPAAABoNmJ4Ng%3D"
)


class _PagedClient(RestGitHubClient):
    """Client whose transport is a canned URL -> ``(document, Link)`` mapping.

    Stubs :meth:`RestGitHubClient._send`, not ``_request``, so the paginated
    helpers exercise the real page walk — which is header-driven since #260 and
    therefore untestable one layer up, where the ``Link`` header does not exist.
    Keys are what the client actually asks for: a relative path for the first
    page, the absolute ``rel="next"`` target for every page after it.
    """

    def __init__(self, pages: dict[str, tuple[object, str]]) -> None:
        super().__init__("vig-os/org-config", "token")
        self.pages = pages
        self.requested: list[str] = []

    def _send(self, method: str, path: str, payload: dict | None = None) -> tuple[object, str]:
        self.requested.append(path)
        return self.pages[path]


def _next_link(url: str) -> str:
    """The ``Link`` header GitHub sends when a further page exists."""
    return f'<{url}>; rel="next"'


def _client() -> RestGitHubClient:
    return RestGitHubClient("vig-os/org-config", "token")


def test_get_json_returns_the_decoded_document(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        assert req.full_url == (
            "https://api.github.com/orgs/vig-os/actions/permissions?per_page=100"
        )
        return stub_response({"sha_pinning_required": True})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _client().get_json("/orgs/vig-os/actions/permissions") == {"sha_pinning_required": True}


def test_http_error_becomes_an_api_error_carrying_the_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApiError) as excinfo:
        _client().get_json("/orgs/vig-os/nope")
    assert excinfo.value.status == 404
    assert "404" in str(excinfo.value)


def test_transport_error_becomes_a_statusless_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    # DNS/TLS/connection failures have no HTTP status; status 0 says "no answer",
    # which is still unreadable rather than drift.
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApiError) as excinfo:
        _client().get_json("/orgs/vig-os")
    assert excinfo.value.status == 0


def test_list_org_secrets_returns_every_page() -> None:
    first = {"secrets": [{"name": f"S{i}", "visibility": "selected"} for i in range(100)]}
    second = {"secrets": [{"name": "LAST", "visibility": "all"}]}
    client = _PagedClient(
        {
            SECRETS_PAGE_1: (first, _next_link(SECRETS_PAGE_2)),
            SECRETS_PAGE_2: (second, ""),
        }
    )
    secrets = client.list_org_secrets(ORG)
    assert len(secrets) == 101
    assert secrets[-1] == {"name": "LAST", "visibility": "all"}
    assert client.requested == [SECRETS_PAGE_1, SECRETS_PAGE_2]


def test_list_org_secret_repositories_returns_names() -> None:
    client = _PagedClient(
        {
            SECRET_REPOS_PAGE_1: (
                {"repositories": [{"name": "devkit"}, {"name": "org-config"}]},
                "",
            )
        }
    )
    assert client.list_org_secret_repositories(ORG, "COMMIT_APP_ID") == ["devkit", "org-config"]


# --- truncation refusal (#258) -------------------------------------------------


@pytest.mark.parametrize(
    ("path", "requested"),
    [
        # No query at all: `?` opens one.
        ("/orgs/vig-os", "/orgs/vig-os?per_page=100"),
        # An existing query: `&` extends it, never a second `?`.
        ("/orgs/vig-os/repos?type=private", "/orgs/vig-os/repos?type=private&per_page=100"),
        # The caller already chose a page size — never duplicated, never overridden.
        ("/orgs/vig-os/repos?per_page=30", "/orgs/vig-os/repos?per_page=30"),
        ("/orgs/vig-os/repos?per_page=30&page=2", "/orgs/vig-os/repos?per_page=30&page=2"),
        ("/orgs/vig-os/repos?page=2&per_page=30", "/orgs/vig-os/repos?page=2&per_page=30"),
        # `per_page` only counts as a parameter NAME: a value spelling it does not.
        ("/orgs/vig-os/repos?q=per_page", "/orgs/vig-os/repos?q=per_page&per_page=100"),
    ],
)
def test_get_json_asks_for_the_largest_page_without_overriding_the_caller(
    monkeypatch: pytest.MonkeyPatch, path: str, requested: str
) -> None:
    seen: list[str] = []

    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        seen.append(req.full_url)
        return stub_response({"ok": True})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    _client().get_json(path)
    assert seen == [f"https://api.github.com{requested}"]


def test_get_json_refuses_a_response_that_is_only_the_first_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The whole point: returning this body would hand the evaluator 30 of N
    # elements, which compares as a shorter set and reads as drift or as clean.
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return stub_response([{"name": f"repo-{i}"} for i in range(30)], {"Link": NEXT_LINK})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TruncatedResponseError) as excinfo:
        _client().get_json("/orgs/vig-os/repos")
    # An ApiError subclass, so every existing degradation path already handles it.
    assert isinstance(excinfo.value, ApiError)
    assert "per_page=100" in str(excinfo.value)


def test_get_json_returns_a_response_whose_link_has_no_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A `Link` header is not itself truncation: the last page of a chain carries
    # `prev`/`first` and is complete as far as the caller asked.
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return stub_response([{"name": "org-config"}], {"Link": LAST_PAGE_LINK})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _client().get_json("/orgs/vig-os/repos?per_page=1&page=14") == [{"name": "org-config"}]


def test_get_json_reads_rel_next_unquoted_too(monkeypatch: pytest.MonkeyPatch) -> None:
    # RFC 8288 allows the bare form; GitHub quotes it, but the guard must not
    # depend on that — a missed `next` is a silently truncated assertion.
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return stub_response([1], {"Link": "<https://api.github.com/x?page=2>; rel=next"})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(TruncatedResponseError):
        _client().get_json("/orgs/vig-os/repos")


def test_a_next_inside_a_link_url_is_not_a_next_page(monkeypatch: pytest.MonkeyPatch) -> None:
    # The guard reads link PARAMETERS, not the URL: a query string spelling
    # `rel=next` must not degrade a complete response.
    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        return stub_response(
            {"ok": True}, {"Link": '<https://api.github.com/x?rel=next>; rel="prev"'}
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _client().get_json("/orgs/vig-os") == {"ok": True}


def test_the_paginated_list_helpers_are_untouched_by_the_guard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # `list_org_repos` walks the pages itself, so a `rel="next"` on page 1 is
    # expected and must not raise — only `get_json` refuses.
    pages = {
        1: [{"name": f"repo-{i}"} for i in range(100)],
        2: [{"name": "last"}],
    }

    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        page = 2 if req.full_url.endswith("page=2") else 1
        link = NEXT_LINK if page == 1 else LAST_PAGE_LINK
        return stub_response(pages[page], {"Link": link})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    assert _client().list_org_repos(ORG)[-1] == "last"


# --- the page walk follows `Link: rel="next"` (#260) ---------------------------


def test_list_org_repos_follows_the_next_link_across_pages() -> None:
    client = _PagedClient(
        {
            REPOS_PAGE_1: ([{"name": f"repo-{i}"} for i in range(100)], _next_link(REPOS_PAGE_2)),
            REPOS_PAGE_2: ([{"name": "last"}], LAST_PAGE_LINK),
        }
    )
    names = client.list_org_repos(ORG)
    assert len(names) == 101
    assert names[-1] == "last"
    assert client.requested == [REPOS_PAGE_1, REPOS_PAGE_2]


def test_list_org_repos_continues_past_a_short_page_that_advertises_next() -> None:
    # The bug (#260): a page shorter than the requested size is not the last
    # page. Endpoints that filter AFTER paginating return one routinely, and the
    # old `len(batch) < 100` stop then swept the rest of the org as if it did
    # not exist — no `undeclared` record for the repos past the cut, and a false
    # `absent` record for every declared one.
    client = _PagedClient(
        {
            REPOS_PAGE_1: ([{"name": f"repo-{i}"} for i in range(30)], _next_link(REPOS_PAGE_2)),
            REPOS_PAGE_2: ([{"name": "last"}], ""),
        }
    )
    names = client.list_org_repos(ORG)
    assert len(names) == 31
    assert names[-1] == "last"
    assert client.requested == [REPOS_PAGE_1, REPOS_PAGE_2]


def test_list_org_repos_stops_on_a_full_page_without_a_next_link() -> None:
    # The mirror of the same mistake: a FULL page is not evidence of a further
    # one. An org of exactly 100 repositories answers without a `Link`, and page
    # 2 would be a request GitHub never invited.
    client = _PagedClient({REPOS_PAGE_1: ([{"name": f"repo-{i}"} for i in range(100)], "")})
    assert len(client.list_org_repos(ORG)) == 100
    assert client.requested == [REPOS_PAGE_1]


def test_list_org_repos_stops_on_a_link_that_names_no_next() -> None:
    # `prev`/`first` on the last page of a chain is a complete answer.
    client = _PagedClient({REPOS_PAGE_1: ([{"name": "org-config"}], LAST_PAGE_LINK)})
    assert client.list_org_repos(ORG) == ["org-config"]
    assert client.requested == [REPOS_PAGE_1]


def test_list_open_drift_issues_follows_the_endpoints_cursor_next_link() -> None:
    # The issues endpoint paginates by CURSOR: its `next` carries an opaque
    # `after=` and it sends no `rel="last"`. Following the URL is the only way
    # to walk it correctly.
    client = _PagedClient(
        {
            ISSUES_PAGE_1: (
                [
                    {"number": 1, "title": "a", "labels": [{"name": "drift"}]},
                    {"number": 2, "title": "pr", "pull_request": {}, "labels": []},
                ],
                _next_link(ISSUES_PAGE_2),
            ),
            ISSUES_PAGE_2: ([{"number": 3, "title": "b", "labels": []}], ""),
        }
    )
    issues = client.list_open_drift_issues()
    assert [issue.number for issue in issues] == [1, 3]
    assert client.requested == [ISSUES_PAGE_1, ISSUES_PAGE_2]


def test_list_org_secrets_continues_past_a_short_page_that_advertises_next() -> None:
    # The envelope shape (`{"secrets": [...]}`) walks by the same header: the
    # page walk yields whole documents and each caller unwraps its own key, so
    # no endpoint knowledge leaks into the walk.
    client = _PagedClient(
        {
            SECRETS_PAGE_1: ({"secrets": [{"name": "A"}]}, _next_link(SECRETS_PAGE_2)),
            SECRETS_PAGE_2: ({"secrets": [{"name": "B"}]}, ""),
        }
    )
    assert [secret["name"] for secret in client.list_org_secrets(ORG)] == ["A", "B"]
    assert client.requested == [SECRETS_PAGE_1, SECRETS_PAGE_2]


def test_a_next_link_with_no_target_is_refused_rather_than_walked_past() -> None:
    # Unreachable against GitHub, but the walk must never turn "there is more"
    # into "that was all": a `next` it cannot follow degrades loudly.
    client = _PagedClient({REPOS_PAGE_1: ([{"name": "org-config"}], '; rel="next"')})
    with pytest.raises(TruncatedResponseError):
        client.list_org_repos(ORG)


def test_a_next_link_that_repeats_a_fetched_page_is_refused_rather_than_walked_forever() -> None:
    # Following the header verbatim costs the walk the ceiling a page counter
    # gave it for free: a `next` that points back at a page already fetched
    # would spin until the job times out. It raises after the repeat is seen,
    # so the second page is fetched exactly once and no third request is made.
    client = _PagedClient(
        {
            REPOS_PAGE_1: ([{"name": "org-config"}], _next_link(REPOS_PAGE_2)),
            REPOS_PAGE_2: ([{"name": "devkit"}], _next_link(REPOS_PAGE_2)),
        }
    )
    with pytest.raises(ApiError, match="pagination cycle"):
        client.list_org_repos(ORG)
    assert client.requested == [REPOS_PAGE_1, REPOS_PAGE_2]


def test_an_api_error_carries_the_response_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 403 is ambiguous; only its headers say whether it was the limiter (#259).

    The rate limiter and the permission boundary both answer `403 Forbidden`, so
    a caller that renders a 403 as a verdict about the resource needs
    `x-ratelimit-remaining` / `retry-after` — which means the error has to carry
    them rather than discard the response.
    """

    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise urllib.error.HTTPError(
            req.full_url,
            403,
            "Forbidden",
            {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1780000000"},
            None,
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApiError) as excinfo:
        _client().get_json("/apps/some-app")
    assert excinfo.value.status == 403
    # Lower-cased on the way in, so a caller never has to guess GitHub's casing.
    assert excinfo.value.headers["x-ratelimit-remaining"] == "0"
    assert excinfo.value.headers["x-ratelimit-reset"] == "1780000000"


def test_a_statusless_api_error_carries_no_headers(monkeypatch: pytest.MonkeyPatch) -> None:
    """No answer means no headers — and an empty mapping, never ``None``."""

    def fake_urlopen(req, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise urllib.error.URLError("connection reset")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ApiError) as excinfo:
        _client().get_json("/apps/some-app")
    assert excinfo.value.headers == {}
