"""
Diff service: compare SOURCE vs TARGET per repo using diffs/commits API (no clone).
Produces per-repo status (aligned/divergent/error), commit count, file list, commit list.
"""

import logging
from typing import Any, Optional

from azure_devops_client import AzureDevOpsClient, AzureDevOpsClientError

logger = logging.getLogger(__name__)

STATUS_ALIGNED = "aligned"
STATUS_DIVERGENT = "divergent"
STATUS_ERROR = "error"

MAX_FILES_DISPLAY = 100
MAX_COMMITS_DISPLAY = 20


def _version_type_from_ref_type(ref_type: str) -> str:
    if ref_type == "branch":
        return "branch"
    if ref_type == "tag_pattern":
        return "tag"
    return "commit"


def get_diff_for_repo(
    client: AzureDevOpsClient,
    repository_id: str,
    repo_name: str,
    source_commit: str,
    target_commit: str,
    source_display: str,
    target_display: str,
    source_ref_type: str,
    target_ref_type: str,
    fetch_commits: bool = True,
) -> dict[str, Any]:
    """
    Compare source vs target for one repo. Uses baseVersion=target, targetVersion=source
    so we get "what's in source that's not in target" (aheadCount = commits in source ahead of target).
    Returns dict with: status, commit_count, file_count, commits, files, note, source_ref, target_ref.
    """
    result = {
        "repo_id": repository_id,
        "repo_name": repo_name,
        "status": STATUS_ERROR,
        "commit_count": 0,
        "file_count": 0,
        "commits": [],
        "files": [],
        "note": "",
        "source_ref": source_display,
        "target_ref": target_display,
        "source_commit": (source_commit or "")[:7],
        "target_commit": (target_commit or "")[:7],
        "source_commit_message": "",
        "source_commit_author": "",
        "source_commit_date": "",
        "target_commit_message": "",
        "target_commit_author": "",
        "target_commit_date": "",
        "ahead_count": 0,
        "behind_count": 0,
    }

    if source_commit == target_commit:
        result["status"] = STATUS_ALIGNED
        result["note"] = "Stesso commit"
        return result

    try:
        # baseVersion=target, targetVersion=source -> diff from target to source (what's ahead in source)
        base_vt = _version_type_from_ref_type(target_ref_type)
        target_vt = _version_type_from_ref_type(source_ref_type)
        # When using commit SHA we must pass versionType=commit
        diff = client.get_diffs_commits(
            repository_id,
            base_version=target_commit,
            target_version=source_commit,
            base_version_type="commit",
            target_version_type="commit",
            top=MAX_FILES_DISPLAY,
        )
    except AzureDevOpsClientError as e:
        result["note"] = e.message or str(e)
        result["source_commit"] = (source_commit or "")[:7]
        result["target_commit"] = (target_commit or "")[:7]
        if e.status_code == 404:
            result["note"] = "Ref non trovato o repository inaccessibile."
        return result

    change_counts = diff.get("changeCounts") or {}
    total_changes = sum(change_counts.values()) if isinstance(change_counts, dict) else 0
    changes = diff.get("changes") or []
    ahead_count = diff.get("aheadCount") or 0
    behind_count = diff.get("behindCount") or 0

    file_paths = []
    for ch in changes[:MAX_FILES_DISPLAY]:
        item = ch.get("item") if isinstance(ch.get("item"), dict) else {}
        path = item.get("path") or item.get("originalPath") or ch.get("path") or ""
        if path:
            file_paths.append(path)
    result["files"] = file_paths
    result["file_count"] = total_changes
    result["ahead_count"] = ahead_count
    result["behind_count"] = behind_count
    result["commit_count"] = ahead_count  # commits in source not in target

    if total_changes == 0 and ahead_count == 0:
        result["status"] = STATUS_ALIGNED
        result["note"] = "Nessuna differenza"
    else:
        result["status"] = STATUS_DIVERGENT
        result["note"] = f"{ahead_count} commit in SOURCE non in TARGET, {total_changes} file modificati"

    if fetch_commits and ahead_count > 0:
        try:
            commits = client.get_commits_compare(
                repository_id,
                source_version=source_commit,
                target_version=target_commit,
                source_version_type="commit",
                target_version_type="commit",
                top=MAX_COMMITS_DISPLAY,
            )
            result["commits"] = [
                {
                    "commitId": c.get("commitId", "")[:7],
                    "comment": (c.get("comment") or "").strip(),
                    "author": (c.get("author") or {}).get("name", ""),
                    "date": (c.get("committer") or c.get("author") or {}).get("date", ""),
                }
                for c in commits
            ]
        except AzureDevOpsClientError:
            result["commits"] = []

    result["source_commit"] = (source_commit or "")[:7]
    result["target_commit"] = (target_commit or "")[:7]
    # Dettaglio messaggio e autore per SOURCE e TARGET commit
    if source_commit:
        src_c = client.get_commit_by_id(repository_id, source_commit)
        if src_c:
            result["source_commit_message"] = (src_c.get("comment") or "").strip()
            result["source_commit_author"] = (src_c.get("author") or {}).get("name", "")
            result["source_commit_date"] = (src_c.get("committer") or src_c.get("author") or {}).get("date", "")
    if target_commit:
        tgt_c = client.get_commit_by_id(repository_id, target_commit)
        if tgt_c:
            result["target_commit_message"] = (tgt_c.get("comment") or "").strip()
            result["target_commit_author"] = (tgt_c.get("author") or {}).get("name", "")
            result["target_commit_date"] = (tgt_c.get("committer") or tgt_c.get("author") or {}).get("date", "")
    return result


def get_diffs_for_repos(
    client: AzureDevOpsClient,
    repositories: list[dict],
    source_resolved: dict[str, dict],
    target_resolved: dict[str, dict],
    source_ref_type: str,
    target_ref_type: str,
) -> list[dict[str, Any]]:
    """
    For each repo, resolve refs and run diff. source/target_resolved: repo_id -> { commit_id, display_ref, error }.
    """
    results = []
    for repo in repositories:
        repo_id = repo.get("id") or repo.get("name")
        repo_name = repo.get("name", str(repo_id))
        if not repo_id:
            results.append({
                "repo_id": repo_id,
                "repo_name": repo_name,
                "status": STATUS_ERROR,
                "commit_count": 0,
                "file_count": 0,
                "commits": [],
                "files": [],
                "note": "Repo senza id",
                "source_ref": "",
                "target_ref": "",
                "source_commit": "",
                "target_commit": "",
            })
            continue

        src = source_resolved.get(repo_id) or {}
        tgt = target_resolved.get(repo_id) or {}

        if src.get("error"):
            results.append({
                "repo_id": repo_id,
                "repo_name": repo_name,
                "status": STATUS_ERROR,
                "commit_count": 0,
                "file_count": 0,
                "commits": [],
                "files": [],
                "note": f"SOURCE: {src.get('error')}",
                "source_ref": src.get("display_ref") or "",
                "target_ref": tgt.get("display_ref") or "",
                "source_commit": (src.get("commit_id") or "")[:7],
                "target_commit": (tgt.get("commit_id") or "")[:7],
            })
            continue
        if tgt.get("error"):
            results.append({
                "repo_id": repo_id,
                "repo_name": repo_name,
                "status": STATUS_ERROR,
                "commit_count": 0,
                "file_count": 0,
                "commits": [],
                "files": [],
                "note": f"TARGET: {tgt.get('error')}",
                "source_ref": src.get("display_ref") or "",
                "target_ref": tgt.get("display_ref") or "",
                "source_commit": (src.get("commit_id") or "")[:7],
                "target_commit": (tgt.get("commit_id") or "")[:7],
            })
            continue

        source_commit = src.get("commit_id")
        target_commit = tgt.get("commit_id")
        if not source_commit or not target_commit:
            results.append({
                "repo_id": repo_id,
                "repo_name": repo_name,
                "status": STATUS_ERROR,
                "commit_count": 0,
                "file_count": 0,
                "commits": [],
                "files": [],
                "note": "Ref non risolto",
                "source_ref": src.get("display_ref") or "",
                "target_ref": tgt.get("display_ref") or "",
                "source_commit": (source_commit or "")[:7],
                "target_commit": (target_commit or "")[:7],
            })
            continue

        r = get_diff_for_repo(
            client,
            repository_id=repo_id,
            repo_name=repo_name,
            source_commit=source_commit,
            target_commit=target_commit,
            source_display=src.get("display_ref") or source_commit[:7],
            target_display=tgt.get("display_ref") or target_commit[:7],
            source_ref_type=source_ref_type,
            target_ref_type=target_ref_type,
            fetch_commits=True,
        )
        results.append(r)

    return results
