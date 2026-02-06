"""
Azure DevOps REST API client with PAT auth, retry/backoff, and core Git endpoints.
No repository cloning; all operations via REST only.
"""

import logging
import time
from typing import Any, Optional
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

API_VERSION = "7.1"
# On-prem (TFS / Azure DevOps Server 2019-2022) spesso non supporta 7.x: usare 5.0 o 6.0
API_VERSION_ONPREM = "5.0"
DEFAULT_BASE = "https://dev.azure.com"
MAX_RETRIES = 3
RETRY_BACKOFF_SEC = 2


class AzureDevOpsClientError(Exception):
    """Raised on API errors (auth, ref not found, server error)."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_text = response_text
        super().__init__(self.message)


class AzureDevOpsClient:
    """Client for Azure DevOps REST API with PAT and optional username."""

    def __init__(
        self,
        organization: str,
        project: str,
        pat: str,
        username: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.organization = organization.strip()
        self.project = project.strip()
        self.pat = pat
        self.username = username or ""
        self.base_url = (base_url or DEFAULT_BASE).rstrip("/")
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(self.username, self.pat)
        self._session.headers["Accept"] = "application/json"
        self._session.headers["Content-Type"] = "application/json"
        self._detected_git_api_version: Optional[str] = None
        # Su alcuni TFS on-prem refs/commits/diffs richiedono il project GUID nel path (da repo.project.id)
        self._project_id: Optional[str] = None

    def _url(self, path: str, query: Optional[dict] = None) -> str:
        base = f"{self.base_url}/{self.organization}"
        # Usa project GUID se impostato (da list_repositories), altrimenti nome progetto
        project_segment = self._project_id or self.project
        if project_segment:
            base = f"{base}/{project_segment}"
        url = f"{base}/_apis{path}"
        if query:
            from urllib.parse import urlencode
            url = f"{url}?{urlencode(query)}"
        return url

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        json: Optional[dict] = None,
        stream: bool = False,
    ) -> Any:
        """Execute request with retry and exponential backoff."""
        url = self._url(path, params)
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = self._session.request(
                    method, url, json=json, timeout=60, stream=stream
                )
                if resp.status_code == 401:
                    raise AzureDevOpsClientError(
                        "Authentication failed (invalid PAT or permissions).",
                        status_code=401,
                        response_text=resp.text,
                    )
                if resp.status_code == 404:
                    raise AzureDevOpsClientError(
                        "Resource not found.",
                        status_code=404,
                        response_text=resp.text,
                    )
                if resp.status_code >= 400:
                    raise AzureDevOpsClientError(
                        f"API error: {resp.status_code}",
                        status_code=resp.status_code,
                        response_text=resp.text,
                    )
                if stream:
                    return resp
                return resp.json() if resp.content else None
            except AzureDevOpsClientError:
                raise
            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    sleep_time = RETRY_BACKOFF_SEC * (2 ** attempt)
                    logger.warning("Request failed, retry in %s s: %s", sleep_time, e)
                    time.sleep(sleep_time)
        raise AzureDevOpsClientError(
            f"Request failed after {MAX_RETRIES} retries: {last_error}"
        )

    def test_connection(self) -> dict:
        """Test connection: call project or core API. Returns minimal project info."""
        path = f"/git/repositories"
        params = {"api-version": API_VERSION, "$top": 1}
        data = self._request("GET", path, params=params)
        return data or {"value": []}

    def discover_git_api_version(self) -> str:
        """
        Scopre quale api-version risponde per le API Git (repositories).
        Non esiste un endpoint ufficiale: si provano 5.0, 6.0, 7.1 e si restituisce la prima che risponde 200 con dati.
        Il risultato viene cachato su self._detected_git_api_version.
        """
        if self._detected_git_api_version:
            return self._detected_git_api_version
        path = "/git/repositories"
        for api_ver in (API_VERSION_ONPREM, "6.0", API_VERSION):
            try:
                data = self._request("GET", path, params={"api-version": api_ver, "$top": 1})
                if data and isinstance(data.get("value"), list):
                    logger.info("discover_git_api_version: usabile api-version=%s", api_ver)
                    self._detected_git_api_version = api_ver
                    return api_ver
            except AzureDevOpsClientError:
                continue
        self._detected_git_api_version = API_VERSION_ONPREM
        return API_VERSION_ONPREM  # fallback conservativo

    def list_repositories(self) -> list[dict]:
        """List all Git repositories in the project. API: Git Repositories List."""
        path = "/git/repositories"
        api_ver = self._detected_git_api_version or self.discover_git_api_version()
        try:
            data = self._request("GET", path, params={"api-version": api_ver})
        except AzureDevOpsClientError:
            data = None
            for v in ("5.0", "6.0", API_VERSION):
                if v == api_ver:
                    continue
                try:
                    data = self._request("GET", path, params={"api-version": v})
                    self._detected_git_api_version = v
                    break
                except AzureDevOpsClientError:
                    continue
        if not data or "value" not in data:
            return []
        repos = data["value"]
        # Salva project GUID dal primo repo (alcuni TFS richiedono GUID nel path per refs/commits/diffs)
        if repos and not self._project_id:
            proj = repos[0].get("project") if isinstance(repos[0], dict) else None
            if isinstance(proj, dict) and proj.get("id"):
                self._project_id = proj["id"]
                logger.debug("Usando project id per path API: %s", self._project_id)
        return repos

    def get_refs(
        self,
        repository_id: str,
        filter_prefix: Optional[str] = None,
        top: int = 1000,
    ) -> list[dict]:
        """List refs (branches/tags) for a repository. Optional filter by prefix (e.g. refs/heads/, refs/tags/)."""
        path = f"/git/repositories/{repository_id}/refs"
        # Su Azure DevOps Server on-prem (TFS) la 7.1 spesso non è supportata: riprova con 6.0 e 5.0
        for api_ver in (API_VERSION, "6.0", API_VERSION_ONPREM):
            params = {"api-version": api_ver, "$top": top}
            if filter_prefix:
                params["filter"] = filter_prefix
            try:
                data = self._request("GET", path, params=params)
            except AzureDevOpsClientError:
                continue
            if not data:
                logger.debug("get_refs: api-version=%s, response body empty", api_ver)
                continue
            # Alcuni server restituiscono "value", altri strutture diverse
            refs = data.get("value") if isinstance(data, dict) else None
            if refs is None:
                refs = data.get("refs") if isinstance(data, dict) else None
            if refs is not None and isinstance(refs, list):
                if not refs and logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        "get_refs: api-version=%s, repo_id=%s, filter=%s, response keys=%s",
                        api_ver, repository_id, filter_prefix, list(data.keys()) if isinstance(data, dict) else None,
                    )
                return refs
            # Risposta senza lista refs (es. formato diverso): prova altra api-version
            logger.debug(
                "get_refs: api-version=%s, no value/refs in response, keys=%s",
                api_ver, list(data.keys()) if isinstance(data, dict) else None,
            )
        # Ultimo tentativo: alcuni TFS espongono i ref senza prefisso refs/heads/; chiedi TUTTI i ref (no filter)
        if filter_prefix and "heads" in filter_prefix:
            for api_ver in (API_VERSION_ONPREM, "6.0", API_VERSION):
                params = {"api-version": api_ver, "$top": top}
                try:
                    data = self._request("GET", path, params=params)
                except AzureDevOpsClientError:
                    continue
                if not data:
                    continue
                refs = data.get("value") or data.get("refs")
                if refs and isinstance(refs, list):
                    # Filtra client-side: considera branch tutto ciò che è refs/heads/X, heads/X o non è un tag
                    def is_branch_like(ref_dict: dict) -> bool:
                        name = (ref_dict.get("name") or "").strip()
                        if name.startswith("refs/tags/"):
                            return False
                        if name.startswith("refs/heads/") or name.startswith("heads/"):
                            return True
                        # Nome corto tipo "master", "CR-Luglio" (nessuno slash refs/...)
                        if "/" not in name or name.startswith("heads/"):
                            return True
                        return False
                    branch_refs = [r for r in refs if is_branch_like(r)]
                    if branch_refs:
                        logger.debug("get_refs: usati %d ref (senza filter) come branch", len(branch_refs))
                        return branch_refs
        return []

    def get_commits(
        self,
        repository_id: str,
        search_criteria: Optional[dict] = None,
        top: int = 1,
    ) -> list[dict]:
        """Get commits. search_criteria can include itemVersion (version, versionType)."""
        path = f"/git/repositories/{repository_id}/commits"
        params = {"api-version": API_VERSION, "$top": top}
        if search_criteria:
            for k, v in search_criteria.items():
                if v is not None:
                    key = k if k.startswith("searchCriteria.") else f"searchCriteria.{k}"
                    params[key] = v
        data = self._request("GET", path, params=params)
        if not data or "value" not in data:
            return []
        return data["value"]

    def get_commits_compare(
        self,
        repository_id: str,
        source_version: str,
        target_version: str,
        source_version_type: str = "commit",
        target_version_type: str = "commit",
        top: int = 20,
    ) -> list[dict]:
        """Get commits in source not in target (for diff list). Uses itemVersion=source, compareVersion=target."""
        path = f"/git/repositories/{repository_id}/commits"
        params = {
            "api-version": API_VERSION,
            "searchCriteria.itemVersion.version": source_version,
            "searchCriteria.itemVersion.versionType": source_version_type,
            "searchCriteria.compareVersion.version": target_version,
            "searchCriteria.compareVersion.versionType": target_version_type,
            "searchCriteria.$top": top,
        }
        data = self._request("GET", path, params=params)
        if not data or "value" not in data:
            return []
        return data["value"]

    def get_annotated_tag(
        self,
        repository_id: str,
        object_id: str,
    ) -> Optional[dict]:
        """Get annotated tag by object ID (for tag date)."""
        path = f"/git/repositories/{repository_id}/annotatedtags/{object_id}"
        params = {"api-version": API_VERSION}
        try:
            return self._request("GET", path, params=params)
        except AzureDevOpsClientError as e:
            if e.status_code == 404:
                return None
            raise

    def get_diffs_commits(
        self,
        repository_id: str,
        base_version: str,
        target_version: str,
        base_version_type: Optional[str] = None,
        target_version_type: Optional[str] = None,
        top: int = 100,
        skip: int = 0,
    ) -> dict:
        """
        Get diff between base and target (merge base and list of changes).
        base_version/target_version: branch name, tag name, or commit SHA.
        base_version_type/target_version_type: 'branch' | 'tag' | 'commit'.
        """
        path = f"/git/repositories/{repository_id}/diffs/commits"
        params = {
            "api-version": API_VERSION,
            "baseVersion": base_version,
            "targetVersion": target_version,
            "$top": top,
            "$skip": skip,
        }
        if base_version_type:
            params["baseVersionType"] = base_version_type
        if target_version_type:
            params["targetVersionType"] = target_version_type
        return self._request("GET", path, params=params) or {}
