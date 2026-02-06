"""
Streamlit UI: configurazione Azure DevOps, selezione repo, definizione ambienti SOURCE/TARGET,
confronto differenze e dashboard risultati. Nessun clone, solo REST API.
"""

import json
import logging
from pathlib import Path

import streamlit as st

from azure_devops_client import AzureDevOpsClient, AzureDevOpsClientError
from ref_resolver import (
    REF_TYPE_BRANCH,
    REF_TYPE_COMMIT,
    REF_TYPE_TAG_PATTERN,
    resolve_refs_for_repos,
)
from diff_service import (
    STATUS_ALIGNED,
    STATUS_DIVERGENT,
    STATUS_ERROR,
    get_diffs_for_repos,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CONFIG_FILE = Path(__file__).resolve().parent / "config.json"
SESSION_PAT = "pat"
SESSION_CLIENT = "client"
SESSION_REPOS = "repos"
SESSION_SELECTED_REPOS = "selected_repos"
SESSION_SOURCE = "source"
SESSION_TARGET = "target"
SESSION_DIFF_RESULTS = "diff_results"

REF_TYPES = [
    ("Branch", REF_TYPE_BRANCH),
    ("Tag pattern", REF_TYPE_TAG_PATTERN),
    ("Commit SHA", REF_TYPE_COMMIT),
]


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Load config failed: %s", e)
        return {}


def save_config(config: dict) -> None:
    # Never persist PAT
    out = {k: v for k, v in config.items() if k not in ("pat", "PAT")}
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Save config failed: %s", e)


def get_client(
    org: str,
    project: str,
    pat: str,
    username: str = "",
    base_url: str = "",
) -> AzureDevOpsClient:
    return AzureDevOpsClient(
        organization=org,
        project=project,
        pat=pat,
        username=username or None,
        base_url=base_url.strip() or None,
    )


def main():
    st.set_page_config(
        page_title="GitCheck - Confronto ambienti Azure DevOps",
        page_icon="🔄",
        layout="wide",
    )
    st.title("🔄 GitCheck – Confronto ambienti (no clone)")
    st.caption("Confronta SOURCE vs TARGET su più repository tramite Azure DevOps REST API.")

    # ----- Config & connection (compatta) -----
    config = load_config()
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            base_url = st.text_input(
                "Base URL (on‑prem, vuoto = cloud)",
                value=config.get("base_url", ""),
                key="base_url",
                placeholder="http://server:8080/tfs",
            )
        with c2:
            org = st.text_input("Organization", value=config.get("organization", ""), key="org", placeholder="DefaultCollection")
        with c3:
            project = st.text_input("Project", value=config.get("project", ""), key="project", placeholder="EACS")
        r2_1, r2_2, r2_3 = st.columns([2, 1, 1])
        with r2_1:
            pat = st.text_input("PAT", type="password", key="pat_input", placeholder="Personal Access Token")
            username = st.text_input("Username (opz.)", value=config.get("username", ""), key="username", placeholder="vuoto per solo PAT")
        with r2_2:
            st.write("")  # allineamento
            st.write("")
            if st.button("Test connessione"):
                if not (org and project and pat):
                    st.error("Inserire Organization, Project e PAT.")
                else:
                    try:
                        client = get_client(org, project, pat, username, base_url)
                        client.test_connection()
                        api_ver = client.discover_git_api_version()
                        st.success(f"OK · Api: **{api_ver}**")
                    except AzureDevOpsClientError as e:
                        st.error(f"Errore: {e.message}")
        with r2_3:
            st.write("")
            st.write("")
            if st.button("Carica repository"):
                if not (org and project and pat):
                    st.error("Org, Project, PAT.")
                else:
                    try:
                        client = get_client(org, project, pat, username, base_url)
                        repos = client.list_repositories()
                        st.session_state[SESSION_REPOS] = repos
                        st.session_state[SESSION_CLIENT] = client
                        st.session_state[SESSION_PAT] = pat
                        st.success(f"**{len(repos)}** repo")
                    except AzureDevOpsClientError as e:
                        st.error(f"Errore: {e.message}")
    st.markdown("---")

    repos = st.session_state.get(SESSION_REPOS) or []
    if not repos:
        st.info("Usa «Carica repository del progetto» per elencare i repository.")
        return

    st.subheader("Repository")
    if SESSION_SELECTED_REPOS not in st.session_state and config.get("selected_repo_ids"):
        st.session_state[SESSION_SELECTED_REPOS] = set(config["selected_repo_ids"])
    selected_ids = st.session_state.get(SESSION_SELECTED_REPOS) or set()
    if isinstance(selected_ids, list):
        selected_ids = set(selected_ids)

    def toggle_all(on: bool):
        if on:
            st.session_state[SESSION_SELECTED_REPOS] = {r.get("id") or r.get("name") for r in repos}
        else:
            st.session_state[SESSION_SELECTED_REPOS] = set()

    # Ordinamento: nome A→Z o Z→A
    sort_order = st.radio("Ordina", options=["Nome (A→Z)", "Nome (Z→A)"], horizontal=True, key="repo_sort")
    repos_sorted = sorted(repos, key=lambda r: (r.get("name") or r.get("id") or "").lower(), reverse=(sort_order == "Nome (Z→A)"))

    all_col, none_col, _ = st.columns([1, 1, 4])
    with all_col:
        if st.button("Seleziona tutti"):
            toggle_all(True)
            st.rerun()
    with none_col:
        if st.button("Deseleziona tutti"):
            toggle_all(False)
            st.rerun()

    # Lista repo in più colonne (3) per usare lo spazio
    N_COLS = 3
    chunk = max(1, (len(repos_sorted) + N_COLS - 1) // N_COLS)
    cols = st.columns(N_COLS)
    for i, repo in enumerate(repos_sorted):
        rid = repo.get("id") or repo.get("name")
        name = repo.get("name", rid)
        checked = rid in selected_ids
        with cols[i % N_COLS]:
            if st.checkbox(name, value=checked, key=f"repo_{rid}"):
                selected_ids.add(rid)
            else:
                selected_ids.discard(rid)
    st.session_state[SESSION_SELECTED_REPOS] = selected_ids

    selected_repos = [r for r in repos if (r.get("id") or r.get("name")) in selected_ids]
    if not selected_repos:
        st.warning("Seleziona almeno un repository.")
        st.stop()

    st.subheader("Definizione ambienti (SOURCE e TARGET)")

    src_config = st.session_state.get(SESSION_SOURCE) or config.get("source") or {}
    tgt_config = st.session_state.get(SESSION_TARGET) or config.get("target") or {}

    # SOURCE e TARGET su una riga ciascuno: [Tipo] [Valore]
    row_src_1, row_src_2 = st.columns([1, 3])
    with row_src_1:
        src_type_index = st.selectbox(
            "Tipo SOURCE",
            options=[0, 1, 2],
            format_func=lambda i: REF_TYPES[i][0],
            index=src_config.get("ref_type_index", 0),
            key="src_type",
        )
    with row_src_2:
        src_value = st.text_input(
            "Valore SOURCE",
            value=src_config.get("value", "develop"),
            key="src_value",
            placeholder="branch, tag pattern (prod*), o SHA",
        )
    st.session_state[SESSION_SOURCE] = {"ref_type_index": src_type_index, "value": src_value}

    row_tgt_1, row_tgt_2 = st.columns([1, 3])
    with row_tgt_1:
        tgt_type_index = st.selectbox(
            "Tipo TARGET",
            options=[0, 1, 2],
            format_func=lambda i: REF_TYPES[i][0],
            index=tgt_config.get("ref_type_index", 0),
            key="tgt_type",
        )
    with row_tgt_2:
        tgt_value = st.text_input(
            "Valore TARGET",
            value=tgt_config.get("value", "master"),
            key="tgt_value",
            placeholder="branch, tag pattern (prod*), o SHA",
        )
    st.session_state[SESSION_TARGET] = {"ref_type_index": tgt_type_index, "value": tgt_value}

    if st.button("Esegui confronto"):
        client = st.session_state.get(SESSION_CLIENT)
        if not client:
            st.error("Esegui prima «Carica repository del progetto».")
            st.stop()

        source_ref_type = REF_TYPES[src_type_index][1]
        target_ref_type = REF_TYPES[tgt_type_index][1]

        with st.spinner("Risolvo ref SOURCE e TARGET per ogni repo..."):
            source_resolved = resolve_refs_for_repos(client, selected_repos, source_ref_type, src_value)
            target_resolved = resolve_refs_for_repos(client, selected_repos, target_ref_type, tgt_value)

        with st.spinner("Calcolo differenze (diffs/commits)..."):
            diff_results = get_diffs_for_repos(
                client,
                selected_repos,
                source_resolved,
                target_resolved,
                source_ref_type,
                target_ref_type,
            )
        st.session_state[SESSION_DIFF_RESULTS] = diff_results
        st.success("Confronto completato.")

    # ----- Dashboard risultati -----
    diff_results = st.session_state.get(SESSION_DIFF_RESULTS)
    if not diff_results:
        st.info("Esegui un confronto per vedere i risultati.")
        if st.button("Salva configurazione (senza PAT)"):
            save_config({
                "base_url": base_url,
                "organization": org,
                "project": project,
                "username": username,
                "selected_repo_ids": list(selected_ids),
                "source": st.session_state.get(SESSION_SOURCE),
                "target": st.session_state.get(SESSION_TARGET),
            })
            st.success("Configurazione salvata in config.json.")
        return

    st.subheader("Dashboard risultati")
    show_only_divergent = st.checkbox("Mostra solo divergenti", value=False, key="filter_div")

    rows = diff_results
    if show_only_divergent:
        rows = [r for r in rows if r.get("status") == STATUS_DIVERGENT]

    def status_icon(s: str):
        if s == STATUS_ALIGNED:
            return "✅ ALLINEATO"
        if s == STATUS_DIVERGENT:
            return "⚠️ DIVERGENTE"
        return "❌ ERRORE"

    for r in rows:
        with st.expander(f"{status_icon(r.get('status', ''))} — {r.get('repo_name', '')}"):
            st.markdown(f"**Stato:** {status_icon(r.get('status', ''))}")
            st.markdown(f"**#Commit diff:** {r.get('commit_count', 0)} | **#File diff:** {r.get('file_count', 0)}")
            st.markdown(f"**SourceRef:** `{r.get('source_ref', '')}` → **TargetRef:** `{r.get('target_ref', '')}`")
            src_commit = r.get("source_commit") or ""
            tgt_commit = r.get("target_commit") or ""

            def _clean(s: str) -> str:
                if not s:
                    return ""
                s = s.strip().rstrip(" -=|")
                return s

            def _fmt_date(iso_date: str) -> str:
                if not iso_date:
                    return ""
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
                    return dt.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    return iso_date[:19] if len(iso_date) >= 19 else iso_date

            if src_commit or tgt_commit:
                st.markdown(f"**SOURCE commit:** `{src_commit}` · **TARGET commit:** `{tgt_commit}`")
                src_msg = _clean(r.get("source_commit_message") or "")
                src_auth = _clean(r.get("source_commit_author") or "")
                src_date = _fmt_date(r.get("source_commit_date") or "")
                tgt_msg = _clean(r.get("target_commit_message") or "")
                tgt_auth = _clean(r.get("target_commit_author") or "")
                tgt_date = _fmt_date(r.get("target_commit_date") or "")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**SOURCE**")
                    if src_commit:
                        st.caption(f"`{src_commit}`" + (f" — *{src_auth}*" if src_auth else ""))
                    if src_date:
                        st.caption(f"📅 {src_date}")
                    st.text(src_msg or "(nessun messaggio)")
                with c2:
                    st.markdown("**TARGET**")
                    if tgt_commit:
                        st.caption(f"`{tgt_commit}`" + (f" — *{tgt_auth}*" if tgt_auth else ""))
                    if tgt_date:
                        st.caption(f"📅 {tgt_date}")
                    st.text(tgt_msg or "(nessun messaggio)")
                st.divider()
            if r.get("note"):
                st.caption(r["note"])

            commits = r.get("commits") or []
            if commits:
                st.markdown("**Commit (SOURCE non in TARGET):**")
                for i, c in enumerate(commits):
                    raw_msg = c.get("comment") or ""
                    msg = _clean(raw_msg) or "(nessun messaggio)"
                    commit_id = (c.get("commitId") or "")[:7]
                    auth = c.get("author")
                    author = auth.get("name", "") if isinstance(auth, dict) else (auth or "")
                    author = _clean(author)
                    raw_date = c.get("date") or ""
                    date_str = _fmt_date(raw_date) if raw_date else ""
                    with st.container():
                        line = f"`{commit_id}`"
                        if author:
                            line += f" — *{author}*"
                        if date_str:
                            line += f" · 📅 {date_str}"
                        st.caption(line)
                        st.text(msg)
                        if i < len(commits) - 1:
                            st.divider()

            files = r.get("files") or []
            if files:
                with st.expander(f"📁 File modificati ({len(files)})", expanded=False):
                    st.text("\n".join(files[:100]))

            repo_id = r.get("repo_id")
            repo_name = r.get("repo_name", "")
            if repo_id and org and project:
                # Link alla compare (cloud o on‑prem)
                t_ref, s_ref = r.get("target_ref", ""), r.get("source_ref", "")
                web_base = (base_url.strip().rstrip("/") or "https://dev.azure.com")
                compare_url = f"{web_base}/{org}/{project}/_git/{repo_name}/branchCompare?baseVersion={t_ref}&targetVersion={s_ref}&_a=commits"
                st.markdown(f"[Apri Compare in Azure DevOps]({compare_url})")

    # Summary table
    st.markdown("---")
    st.markdown("**Riepilogo**")
    summary = [
        {"Repo": r.get("repo_name"), "Stato": status_icon(r.get("status", "")), "#Commit diff": r.get("commit_count", 0), "#File diff": r.get("file_count", 0), "SourceRef": r.get("source_ref", ""), "TargetRef": r.get("target_ref", ""), "Note": r.get("note", "")}
        for r in diff_results
    ]
    st.dataframe(summary, use_container_width=True, hide_index=True)

    if st.button("Salva configurazione (senza PAT)"):
        save_config({
            "base_url": base_url,
            "organization": org,
            "project": project,
            "username": username,
            "selected_repo_ids": list(st.session_state.get(SESSION_SELECTED_REPOS) or set()),
            "source": st.session_state.get(SESSION_SOURCE),
            "target": st.session_state.get(SESSION_TARGET),
        })
        st.success("Configurazione salvata in config.json.")


if __name__ == "__main__":
    main()
