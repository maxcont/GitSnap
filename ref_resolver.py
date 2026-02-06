"""
Resolves environment ref (branch, tag pattern, or commit SHA) to a concrete commit ID per repository.
Tag pattern: lists tags matching pattern and selects the most recent by commit date.
"""

import fnmatch
import logging
from typing import Optional

from azure_devops_client import AzureDevOpsClient, AzureDevOpsClientError

logger = logging.getLogger(__name__)

REF_TYPE_BRANCH = "branch"
REF_TYPE_TAG_PATTERN = "tag_pattern"
REF_TYPE_COMMIT = "commit"


def _tag_name_from_ref(ref_name: str) -> str:
    """refs/tags/foo -> foo"""
    if ref_name.startswith("refs/tags/"):
        return ref_name[len("refs/tags/"):]
    return ref_name


def _branch_short_name(ref_name: str) -> Optional[str]:
    """Estrae il nome corto da ref (refs/heads/X, heads/X o X)."""
    if not ref_name:
        return None
    ref_name = ref_name.strip()
    if ref_name.startswith("refs/heads/"):
        return ref_name[len("refs/heads/"):]
    if ref_name.startswith("heads/"):
        return ref_name[len("heads/"):]
    # Nome corto senza prefisso (es. master, CR-Luglio)
    if not ref_name.startswith("refs/tags/"):
        return ref_name
    return None


def resolve_ref_for_repo(
    client: AzureDevOpsClient,
    repository_id: str,
    ref_type: str,
    ref_value: str,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Resolve ref to (commit_id, display_ref, error_message).
    display_ref is the resolved ref to show (e.g. tag name chosen for tag pattern).
    """
    ref_value = (ref_value or "").strip()
    if not ref_value:
        return None, None, "Ref value is empty."

    if ref_type == REF_TYPE_COMMIT:
        if len(ref_value) < 7:
            return None, None, "Commit SHA too short."
        return ref_value, ref_value[:7], None

    if ref_type == REF_TYPE_BRANCH:
        wanted = ref_value
        all_heads = client.get_refs(repository_id, filter_prefix="refs/heads/", top=1000)
        if not all_heads:
            return None, None, f"Branch not found: {ref_value}"

        candidates = []
        for r in all_heads:
            full = (r.get("name") or "").strip()
            short = _branch_short_name(full)
            if short is None:
                continue
            candidates.append((full, short, r.get("objectId")))

        exact = [c for c in candidates if c[1] == wanted]
        if exact:
            full, short, obj_id = exact[0]
            if obj_id:
                return obj_id, short, None

        ci = [c for c in candidates if c[1].lower() == wanted.lower()]
        if ci:
            full, short, obj_id = ci[0]
            if obj_id:
                return obj_id, short, None

        suffix = [c for c in candidates if c[0].endswith("/" + wanted)]
        if suffix:
            full, short, obj_id = suffix[0]
            if obj_id:
                return obj_id, short, None

        logger.debug(
            "Branch '%s' not found in repo %s. Available heads: %s",
            ref_value,
            repository_id,
            [c[1] for c in candidates],
        )
        return None, None, f"Branch not found: {ref_value}"

    if ref_type == REF_TYPE_TAG_PATTERN:
        all_tags = client.get_refs(repository_id, filter_prefix="refs/tags/", top=1000)
        tag_refs = [r for r in all_tags if r.get("name", "").startswith("refs/tags/")]
        matching = []
        for r in tag_refs:
            tag_name = _tag_name_from_ref(r.get("name", ""))
            if fnmatch.fnmatch(tag_name, ref_value):
                matching.append((tag_name, r.get("objectId")))

        if not matching:
            return None, None, f"No tags matching pattern: {ref_value}"

        # Resolve each tag to commit + date; lightweight tag objectId may be commit already
        tag_commits: list[tuple[str, str, Optional[str]]] = []  # (tag_name, commit_id, date_str)
        for tag_name, obj_id in matching:
            if not obj_id:
                continue
            # Get commit for this ref (versionType=Tag, version=tag_name)
            try:
                commits = client.get_commits(
                    repository_id,
                    search_criteria={
                        "itemVersion.version": tag_name,
                        "itemVersion.versionType": "tag",
                    },
                    top=1,
                )
                if commits:
                    c = commits[0]
                    commit_id = c.get("commitId")
                    date_str = c.get("committer", {}).get("date") or c.get("author", {}).get("date") or ""
                    if commit_id:
                        tag_commits.append((tag_name, commit_id, date_str))
                else:
                    # Lightweight tag: objectId might be the commit
                    tag_commits.append((tag_name, obj_id, ""))
            except AzureDevOpsClientError:
                tag_commits.append((tag_name, obj_id, ""))

        if not tag_commits:
            return None, None, f"No resolvable tags for pattern: {ref_value}"

        # Sort by date descending (most recent first); empty date last
        tag_commits.sort(key=lambda x: (x[2] or "0000"), reverse=True)
        chosen_name, chosen_commit, _ = tag_commits[0]
        return chosen_commit, chosen_name, None

    return None, None, f"Unknown ref type: {ref_type}"


def resolve_refs_for_repos(
    client: AzureDevOpsClient,
    repositories: list[dict],
    ref_type: str,
    ref_value: str,
) -> dict[str, dict]:
    """
    For each repo, resolve ref. Returns dict: repo_id -> { "commit_id", "display_ref", "error" }.
    """
    result = {}
    for repo in repositories:
        repo_id = repo.get("id") or repo.get("name")
        name = repo.get("name", repo_id)
        if not repo_id:
            result[name] = {"commit_id": None, "display_ref": None, "error": "No repo id"}
            continue
        commit_id, display_ref, error = resolve_ref_for_repo(
            client, repo_id, ref_type, ref_value
        )
        result[repo_id] = {
            "commit_id": commit_id,
            "display_ref": display_ref or ref_value,
            "error": error,
        }
    return result
