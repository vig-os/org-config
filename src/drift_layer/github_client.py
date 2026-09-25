"""GitHub client injected at the edge (ADR-0007).

The pure core (parser/reconcile) never touches the network; this is the only
module that does. :class:`GitHubClient` is the Protocol the core depends on, so
tests inject a fake. :class:`RestGitHubClient` is the production implementation
over the GitHub REST API using the standard library only — no third-party
runtime dependency, keeping the tool ``uvx``-light like otterdog (ADR-0005).

The client is constructed with an *issues:write*-narrowed token (the drift
workflow's second, least-privilege token); narrowing works fine for issues. The
org/repo READ surface (inventory sweep, unmanaged-control assertions) needs the
full org-wide token instead, so the CLI builds a second client for it.

Every transport failure surfaces as an :class:`ApiError` carrying the HTTP
status, because the unmanaged-controls leg (issue #116) must tell "the control
is wrong" apart from "the control could not be read" — a 403 on one row has to
degrade that row, never be reported as drift or silently resolve its issue. The
error carries the refusal's response headers for the same reason: a ``403`` from
the rate limiter and a ``403`` from the permission boundary are indistinguishable
by status and reason phrase, and only ``x-ratelimit-remaining`` / ``retry-after``
separate them (issue #259).

For the same reason :meth:`RestGitHubClient.get_json` refuses an INCOMPLETE
answer (issue #258): it asks for the largest page GitHub serves and raises
:class:`TruncatedResponseError` when the response advertises a further one, so a
row projecting over a list can never assert the first page of a longer
collection as if it were the whole of it.

The list methods resolve their collections instead of refusing them, through one
shared page walk (:meth:`RestGitHubClient._paginate`) that reads the same
header: it follows ``Link: rel="next"`` until GitHub stops sending one (issue
#260). Deciding from the SIZE of a page — the walk this replaced — is an
inference about GitHub's behaviour rather than a reading of what GitHub said,
and it is wrong in both directions: an endpoint that filters after paginating
returns a short page that is not the last, and a collection that ends exactly on
a page boundary returns a full page that is.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterator, Mapping
from typing import Protocol

from .models import Issue, IssueAction

_API_ROOT = "https://api.github.com"

# The largest page GitHub serves. `get_json` asks for it so the one GET it makes
# resolves collections up to this size completely; past it the read is refused
# rather than truncated (issue #258). The page walk asks for it too, to make the
# fewest round trips — but never to decide where the collection ends (#260).
_MAX_PAGE_SIZE = 100


class ApiError(Exception):
    """A failed GitHub API call, carrying the HTTP status for triage.

    ``status`` is the HTTP code (404 unassertable, 401/403 token scope, 5xx
    upstream) or ``0`` when the request never got an answer at all — DNS, TLS,
    connection or decode failure. Zero is still "unreadable", not "absent".

    ``headers`` carries the refusal's response headers, lower-cased, because the
    status alone does not say what a ``403`` means: GitHub answers ``403`` both
    for "this credential may not read this resource" and for rate-limit
    exhaustion, with the same reason phrase. ``x-ratelimit-remaining`` and
    ``retry-after`` are the only signals that tell the two apart, so a caller
    that reports a ``403`` as a verdict about the resource (issue #259) must be
    able to see them. Empty when the request never got an answer.
    """

    def __init__(self, status: int, message: str, headers: Mapping[str, str] | None = None) -> None:
        super().__init__(f"{status}: {message}" if status else message)
        self.status = status
        self.headers: dict[str, str] = {
            str(name).lower(): str(value) for name, value in (headers or {}).items()
        }


class TruncatedResponseError(ApiError):
    """A 200 that answered only the first page of a longer collection.

    The one :class:`ApiError` whose status is a SUCCESS: the request worked,
    the answer is incomplete. It is an ``ApiError`` subclass on purpose — every
    caller already degrades the row it belongs to rather than guessing, and
    "could not resolve the whole collection" wants exactly that treatment. The
    alternative, returning the partial body, is the one outcome the table must
    never produce: a projection over it compares as a shorter set and reads as
    drift or, worse, as clean (issue #258).
    """

    def __init__(self, path: str) -> None:
        super().__init__(
            200,
            f'GET {path}: one page of a longer collection (Link: rel="next") — '
            f"a partial answer cannot stand in for the whole collection",
        )


class GitHubClient(Protocol):
    """The issue operations the reconciler's executor needs."""

    def list_open_drift_issues(self) -> list[Issue]: ...

    def list_org_repos(self, org: str) -> list[str]: ...

    def get_json(self, path: str) -> object: ...

    def list_org_secrets(self, org: str) -> list[dict]: ...

    def list_org_secret_repositories(self, org: str, name: str) -> list[str]: ...

    def create_issue(self, title: str, body: str, labels: tuple[str, ...]) -> int: ...

    def update_issue(self, number: int, title: str, body: str) -> None: ...

    def add_comment(self, number: int, body: str) -> None: ...

    def close_issue(self, number: int) -> None: ...


class RestGitHubClient:
    """Standard-library REST client for one ``owner/repo``."""

    def __init__(self, repo: str, token: str, *, api_root: str = _API_ROOT) -> None:
        self._repo = repo
        self._token = token
        self._api_root = api_root.rstrip("/")

    def _request(self, method: str, path: str, payload: dict | None = None) -> object:
        """Send one request and return the decoded body, discarding headers."""
        document, _ = self._send(method, path, payload)
        return document

    def _send(self, method: str, path: str, payload: dict | None = None) -> tuple[object, str]:
        """Send one request and return ``(document, Link header)``.

        The pagination-aware sibling of :meth:`_request`, and the only place the
        response headers survive the ``urlopen`` block. Two readers need them:
        ``get_json``, to refuse a partial answer (#258), and :meth:`_paginate`,
        to know whether there is another page (#260). ``path`` may be a full URL,
        which is what a ``rel="next"`` target is.
        """
        url = path if path.startswith("http") else f"{self._api_root}{path}"
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Authorization", f"Bearer {self._token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read()
                link = resp.headers.get("Link", "") or ""
            return (json.loads(raw) if raw else None), link
        except urllib.error.HTTPError as exc:
            raise ApiError(
                exc.code, f"{method} {path}: {exc.reason}", dict(exc.headers.items())
            ) from exc
        except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
            raise ApiError(0, f"{method} {path}: {exc}") from exc

    def _paginate(self, path: str) -> Iterator[object]:
        """Walk every page of ``path``, yielding one decoded document per page.

        The stop condition is the ``Link`` header and nothing else (issue #260).
        A page shorter than the one asked for is not evidence that it is the
        last — an endpoint that filters after paginating returns short pages
        routinely — and a full page is not evidence that another follows. Only
        ``rel="next"`` says there is more, and its absence says there is not;
        that is what GitHub documents, and it is the only signal that stays
        correct as the fleet grows past one page.

        The ``next`` target is followed **verbatim**, never rebuilt from a page
        number: it carries the page size, the org's numeric id and — on the
        cursor-paginated issues endpoint — an opaque ``after=`` that no composed
        ``page=N`` reproduces. A ``next`` that cannot be followed raises
        :class:`TruncatedResponseError` rather than ending the walk quietly,
        because "there is more" must never be read as "that was all".

        Following a URL rather than composing one costs the walk the ceiling a
        page counter gave it for free, so it carries its own: a ``next`` target
        already fetched is a cycle, and the walk raises instead of spinning on
        it until the job's ``timeout-minutes`` burns the rate limit. Bounding it
        here rather than with a page cap keeps the bound on the thing that
        actually goes wrong — a server repeating itself — and never refuses a
        genuinely long collection.

        Whole documents are yielded rather than merged rows: GitHub answers a
        list endpoint in two shapes — a root list (``/orgs/{org}/repos``) and an
        envelope keyed per endpoint (``secrets``, ``repositories``) — and which
        one it is belongs to the caller, not to the transport.
        """
        url = _with_max_page_size(path)
        fetched: set[str] = set()
        while url:
            fetched.add(url)
            document, link = self._send("GET", url)
            yield document
            following = _next_page_url(link)
            if not following and _advertises_next_page(link):
                raise TruncatedResponseError(url)
            if following in fetched:
                raise ApiError(
                    200,
                    f'GET {url}: the rel="next" target {following} was already fetched — '
                    f"refusing to walk a pagination cycle",
                )
            url = following

    def list_open_drift_issues(self) -> list[Issue]:
        """List open issues labelled ``drift`` (the reconciler filters further)."""
        issues: list[Issue] = []
        for document in self._paginate(f"/repos/{self._repo}/issues?state=open&labels=drift"):
            for raw in document or []:
                # The issues endpoint also returns PRs; skip them.
                if "pull_request" in raw:
                    continue
                issues.append(
                    Issue(
                        number=raw["number"],
                        title=raw.get("title", ""),
                        body=raw.get("body") or "",
                        state=raw.get("state", "open"),
                        labels=tuple(
                            label.get("name", "")
                            for label in raw.get("labels", [])
                            if isinstance(label, dict)
                        ),
                    )
                )
        return issues

    def list_org_repos(self, org: str) -> list[str]:
        """List every repo name in ``org`` (``GET /orgs/{org}/repos``).

        Paginated over :meth:`_paginate`, so the walk ends where GitHub says it
        does; the org endpoint defaults to ``type=all`` (public + private,
        including archived), so the sweep sees the full live inventory. Needs an
        org-wide read token — the drift workflow's full plan token, not the
        issues-narrowed one.

        Completeness is the contract here, not a nicety: this list is the
        ``live`` side of the ADR-0002 inventory sweep, and a short one fails in
        both directions at once — a repo past the cut never produces its
        ``undeclared`` record (the shadow-repo finding goes silently missing),
        and a declared repo past the cut produces a false ``absent`` one
        (issue #260)."""
        names: list[str] = []
        for document in self._paginate(f"/orgs/{org}/repos"):
            names.extend(raw["name"] for raw in document or [])
        return names

    def get_json(self, path: str) -> object:
        """GET one endpoint and return the decoded JSON document, or refuse.

        The generic read the unmanaged-controls leg asserts against (issue
        #116); the row's dotted path does the field selection, so the client
        stays a dumb transport and every control is reachable without a new
        method per endpoint.

        Still one GET — but never a silently partial one (issue #258). The path
        gets ``per_page=100`` unless it already chose a page size, and a
        response advertising ``rel="next"`` raises
        :class:`TruncatedResponseError` instead of returning page 1. The refusal
        is unconditional rather than reserved for list-shaped rows, because the
        transport cannot see the row's path: a dict-shaped endpoint never sends
        a ``next`` anyway, and over-refusing a scalar read only degrades that
        one row, while under-refusing a projection asserts a lie."""
        requested = _with_max_page_size(path)
        document, link = self._send("GET", requested)
        if _advertises_next_page(link):
            raise TruncatedResponseError(requested)
        return document

    def list_org_secrets(self, org: str) -> list[dict]:
        """List the org's Actions secrets (name + visibility), paginated.

        Values are never returned by the API — only the metadata the
        org-secret assertion families compare against the committed config."""
        secrets: list[dict] = []
        for document in self._paginate(f"/orgs/{org}/actions/secrets"):
            if isinstance(document, dict):
                secrets.extend(document.get("secrets", []))
        return secrets

    def list_org_secret_repositories(self, org: str, name: str) -> list[str]:
        """List the repos a ``selected``-visibility org secret is shared with."""
        names: list[str] = []
        for document in self._paginate(f"/orgs/{org}/actions/secrets/{name}/repositories"):
            if isinstance(document, dict):
                names.extend(raw["name"] for raw in document.get("repositories", []))
        return names

    def create_issue(self, title: str, body: str, labels: tuple[str, ...]) -> int:
        result = self._request(
            "POST",
            f"/repos/{self._repo}/issues",
            {"title": title, "body": body, "labels": list(labels)},
        )
        return result["number"]  # type: ignore[index]

    def update_issue(self, number: int, title: str, body: str) -> None:
        self._request(
            "PATCH",
            f"/repos/{self._repo}/issues/{number}",
            {"title": title, "body": body},
        )

    def add_comment(self, number: int, body: str) -> None:
        self._request(
            "POST",
            f"/repos/{self._repo}/issues/{number}/comments",
            {"body": body},
        )

    def close_issue(self, number: int) -> None:
        self._request(
            "PATCH",
            f"/repos/{self._repo}/issues/{number}",
            {"state": "closed", "state_reason": "completed"},
        )


def _with_max_page_size(path: str) -> str:
    """Add ``per_page=100`` unless the path already names a page size.

    Joins with ``&`` when a query string is already there and ``?`` when it is
    not, and works on a full URL as well as an API path. GitHub ignores query
    parameters an endpoint does not define (verified against ``GET /orgs/{org}``,
    which answers normally with ``per_page`` attached), so a non-paginated
    endpoint is unaffected.
    """
    head, separator, query = path.partition("?")
    parts = query.split("&") if query else []
    if separator and any(part.partition("=")[0] == "per_page" for part in parts):
        return path
    return head + "?" + "&".join([*parts, f"per_page={_MAX_PAGE_SIZE}"])


def _advertises_next_page(link: str) -> bool:
    """Whether a ``Link`` header names a further page.

    Reads the link PARAMETERS only, so a target URL that happens to contain
    ``rel=next`` is not mistaken for one, and accepts the unquoted RFC 8288
    spelling as well as the quoted form GitHub sends.
    """
    return any(_names_next(params) for _, params in _link_entries(link))


def _next_page_url(link: str) -> str:
    """The ``rel="next"`` target of a ``Link`` header, or ``""`` if there is none.

    Returned verbatim, because it is not reconstructible: GitHub's next URL
    carries the page size, the org rewritten to its numeric id and, on a
    cursor-paginated endpoint such as ``/repos/{owner}/{repo}/issues``, an
    opaque ``after=`` cursor. Empty for an entry whose target is missing or
    unbracketed — which is not a link at all (RFC 8288), and which
    :meth:`RestGitHubClient._paginate` refuses rather than walks past.
    """
    for target, params in _link_entries(link):
        if _names_next(params) and target:
            return target
    return ""


def _link_entries(link: str) -> Iterator[tuple[str, str]]:
    """Split a ``Link`` header into ``(target URL, parameters)`` pairs.

    The target is returned only when it is bracketed as RFC 8288 requires, so
    the two readers above agree on what counts as a link.
    """
    for entry in link.split(","):
        head, _, params = entry.partition(";")
        before, bracketed, rest = head.strip().partition("<")
        url, closed, _ = rest.partition(">")
        yield (url if not before and bracketed and closed else ""), params


def _names_next(params: str) -> bool:
    """Whether a link's parameters include ``rel=next``, quoted or bare."""
    return any(
        param.strip().replace('"', "").replace("'", "").replace(" ", "") == "rel=next"
        for param in params.split(";")
    )


def execute(actions: list[IssueAction], client: GitHubClient, labels: tuple[str, ...]) -> None:
    """Apply reconciler actions through the client (open/update/close)."""
    for action in actions:
        if action.kind == "open":
            number = client.create_issue(action.title, action.body, labels)
            if action.comment:
                client.add_comment(number, action.comment)
        elif action.kind == "update":
            assert action.number is not None
            client.update_issue(action.number, action.title, action.body)
            if action.comment:
                client.add_comment(action.number, action.comment)
        elif action.kind == "close":
            assert action.number is not None
            if action.comment:
                client.add_comment(action.number, action.comment)
            client.close_issue(action.number)
        else:  # pragma: no cover - defensive
            msg = f"unknown action kind: {action.kind}"
            raise ValueError(msg)
