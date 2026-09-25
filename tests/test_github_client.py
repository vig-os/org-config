"""L1 tests for the REST client's read surface and typed API errors (#116).

The unmanaged-controls leg has to tell "the control is wrong" apart from "the
control could not be read", so every transport failure must arrive as an
:class:`ApiError` carrying a status the evaluator can branch on. No network
here: ``urlopen`` is stubbed and the paginated helpers run against a fake
``_request``.
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


class _RecordingClient(RestGitHubClient):
    """Client whose transport is a canned path -> response mapping."""

    def __init__(self, responses: dict[str, object]) -> None:
        super().__init__("vig-os/org-config", "token")
        self.responses = responses
        self.requested: list[str] = []

    def _request(self, method: str, path: str, payload: dict | None = None) -> object:
        self.requested.append(path)
        return self.responses[path]


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


def test_list_org_secrets_returns_every_page(monkeypatch: pytest.MonkeyPatch) -> None:
    first = {"secrets": [{"name": f"S{i}", "visibility": "selected"} for i in range(100)]}
    second = {"secrets": [{"name": "LAST", "visibility": "all"}]}
    client = _RecordingClient(
        {
            f"/orgs/{ORG}/actions/secrets?per_page=100&page=1": first,
            f"/orgs/{ORG}/actions/secrets?per_page=100&page=2": second,
        }
    )
    secrets = client.list_org_secrets(ORG)
    assert len(secrets) == 101
    assert secrets[-1] == {"name": "LAST", "visibility": "all"}
    assert len(client.requested) == 2


def test_list_org_secret_repositories_returns_names(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _RecordingClient(
        {
            f"/orgs/{ORG}/actions/secrets/COMMIT_APP_ID/repositories?per_page=100&page=1": {
                "repositories": [{"name": "devkit"}, {"name": "org-config"}]
            }
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
