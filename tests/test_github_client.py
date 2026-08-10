"""L1 tests for the REST client's read surface and typed API errors (#116).

The unmanaged-controls leg has to tell "the control is wrong" apart from "the
control could not be read", so every transport failure must arrive as an
:class:`ApiError` carrying a status the evaluator can branch on. No network
here: ``urlopen`` is stubbed and the paginated helpers run against a fake
``_request``.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from io import BytesIO

import pytest

from drift_layer.github_client import ApiError, RestGitHubClient

ORG = "vig-os"


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
        assert req.full_url == "https://api.github.com/orgs/vig-os/actions/permissions"
        return _response({"sha_pinning_required": True})

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


def _response(document: object) -> object:
    class _Ctx:
        def __enter__(self):  # noqa: ANN204
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def read(self) -> bytes:
            return BytesIO(json.dumps(document).encode()).read()

    return _Ctx()
