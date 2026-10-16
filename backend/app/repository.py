"""Allowlisted read-only GitHub REST adapter and pinned PostgreSQL retrieval."""

import base64
import re
from pathlib import PurePosixPath
from typing import Protocol
from urllib.parse import quote
import httpx
from sqlalchemy import select, func, or_
from app.config import get_settings
from app.models import SourceChunk


def normalize_path(path: str) -> str:
    path = path.replace("\\", "/")
    parts = path.split("/")
    if (
        not path
        or path.startswith("/")
        or any(p == ".." for p in parts)
        or ":" in path
        or "\x00" in path
    ):
        raise ValueError("Unsafe repository path")
    normalized = str(PurePosixPath(path))
    if normalized == "." or len(normalized) > 400:
        raise ValueError("Unsafe repository path")
    return normalized


def protected(path: str, policies: list[str]) -> bool:
    path = normalize_path(path).casefold()
    for policy in policies:
        prefix = normalize_path(policy.rstrip("/*")).casefold()
        if path == prefix or path.startswith(prefix + "/"):
            return True
    return False


class RepositoryProvider(Protocol):
    def resolve_commit(self, owner: str, repo: str, ref: str) -> str: ...
    def read_file(self, owner: str, repo: str, path: str, commit: str) -> str: ...
    def get_issue(self, owner: str, repo: str, number: int) -> dict: ...


class GitHubREST:
    def __init__(
        self, owner: str, repo: str, paths: list[str], token: str = "", transport=None
    ):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+", repo
        ):
            raise ValueError("Invalid repository metadata")
        self.owner, self.repo = owner, repo
        self.paths = {normalize_path(p) for p in paths}
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            headers["Authorization"] = "Bearer " + token
        self.client = httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=12,
            transport=transport,
            follow_redirects=False,
        )

    def _get(self, owner, repo, suffix):
        if (owner, repo) != (self.owner, self.repo):
            raise ValueError("Repository is not allowlisted")
        response = self.client.get(f"/repos/{owner}/{repo}/{suffix}")
        response.raise_for_status()
        if len(response.content) > 300_000:
            raise ValueError("Repository response too large")
        return response.json()

    def resolve_commit(self, owner, repo, ref):
        data = self._get(owner, repo, "commits/" + quote(ref, safe=""))
        sha = data["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("Invalid pinned commit")
        return sha

    def read_file(self, owner, repo, path, commit):
        path = normalize_path(path)
        if (
            path not in self.paths
            or not path.endswith((".md", ".py"))
            or not re.fullmatch(r"[0-9a-f]{40}", commit)
        ):
            raise ValueError("Source is not allowlisted")
        if any(
            part.startswith(".") or "secret" in part.casefold()
            for part in path.split("/")
        ):
            raise ValueError("Secret-bearing path excluded")
        data = self._get(owner, repo, f"contents/{quote(path, safe='/')}?ref={commit}")
        if (
            data.get("type") != "file"
            or data.get("encoding") != "base64"
            or data.get("size", 0) > 100_000
        ):
            raise ValueError("Unsupported source")
        raw = base64.b64decode(data["content"], validate=False)
        if b"\x00" in raw:
            raise ValueError("Binary source excluded")
        value = raw.decode("utf-8")
        if re.search(
            r"(?:ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{24,}|BEGIN .*PRIVATE KEY)", value
        ):
            raise ValueError("Possible secret excluded")
        return value

    def get_issue(self, owner, repo, number):
        if not isinstance(number, int) or number <= 0:
            raise ValueError("Invalid issue")
        data = self._get(owner, repo, f"issues/{number}")
        return {
            "number": data["number"],
            "title": data["title"][:500],
            "body": (data.get("body") or "")[:8000],
        }


def provider_for(project):
    settings = get_settings()
    if settings.repository_provider != "github_rest":
        raise ValueError("Only the verified github_rest runtime adapter is configured")
    if (project.owner, project.name) != (settings.github_owner, settings.github_repo):
        raise ValueError("Project is outside the runtime repository allowlist")
    return GitHubREST(
        project.owner, project.name, project.allowed_paths, settings.github_token
    )


def citation(source, project, start=None, end=None):
    start = source.start_line if start is None else start
    end = source.end_line if end is None else end
    if not source.start_line <= start <= end <= source.end_line:
        raise ValueError("Citation outside source bounds")
    if not re.fullmatch(r"[0-9a-f]{40}", source.commit_sha):
        raise ValueError("Source commit is not pinned")
    excerpt = "\n".join(
        source.content.splitlines()[
            start - source.start_line : end - source.start_line + 1
        ]
    )
    return {
        "source_id": source.id,
        "path": source.path,
        "commit_sha": source.commit_sha,
        "start_line": start,
        "end_line": end,
        "excerpt": excerpt,
        "url": f"https://github.com/{project.owner}/{project.name}/blob/{source.commit_sha}/{quote(source.path, safe='/')}#L{start}-L{end}",
    }


def search_sources(db, project, query, limit=8):
    base = select(SourceChunk).where(
        SourceChunk.project_id == project.id,
        SourceChunk.commit_sha == project.commit_sha,
    )
    text_query = func.plainto_tsquery("simple", query[:1000])
    found = list(
        db.scalars(
            base.where(SourceChunk.search_document.op("@@")(text_query)).limit(limit)
        )
    )
    if len(found) < limit:
        terms = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", query)[:10]
        if terms:
            matches = or_(
                *(
                    or_(
                        SourceChunk.path.ilike(f"%{term}%"),
                        SourceChunk.content.ilike(f"%{term}%"),
                    )
                    for term in terms
                )
            )
            for source in db.scalars(
                base.where(matches).order_by(SourceChunk.path).limit(limit)
            ):
                if source.id not in {s.id for s in found}:
                    found.append(source)
    # Include both sides of the explicitly configured demo consistency question.
    return found[:limit]
