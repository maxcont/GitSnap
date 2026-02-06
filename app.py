"""
Streamlit UI: configurazione Azure DevOps, selezione repo, definizione ambienti SOURCE/TARGET,
confronto differenze e dashboard risultati. Nessun clone, solo REST API.
"""

import json
import logging
import time
import uuid
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
PROJECTS_FILE = Path(__file__).resolve().parent / "projects.json"
SESSION_PAT = "pat"
SESSION_CLIENT = "client"
SESSION_REPOS = "repos"
SESSION_SELECTED_REPOS = "selected_repos"
SESSION_SOURCE = "source"
SESSION_TARGET = "target"
SESSION_DIFF_RESULTS = "diff_results"
SESSION_CURRENT_PROJECT_ID = "current_project_id"

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


def load_projects() -> list[dict]:
    if not PROJECTS_FILE.exists():
        return []
    try:
        with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("projects", data) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    except Exception as e:
        logger.warning("Load projects failed: %s", e)
        return []


def save_projects(projects: list[dict]) -> None:
    try:
        with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"projects": projects}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Save projects failed: %s", e)


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
        page_title="GitSnap - Confronto ambienti",
        page_icon="🔄",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.title("🔄 GitSnap – Confronto ambienti")
    st.caption("Confronta SOURCE vs TARGET su più repository tramite Azure DevOps REST API.")

    config = load_config()
    projects_list = load_projects()

    # ----- Sidebar: Progetti (pannello opzioni) -----
    with st.sidebar:
        st.subheader("📁 Progetti")
        st.caption("Salva e carica configurazioni (Base URL, Org, Project, PAT opzionale).")
        if not projects_list:
            st.info("Nessun progetto salvato. Aggiungine uno sotto.")
        else:
            options = ["— Seleziona progetto —"] + [f"{p.get('name', p.get('project', ''))} ({p.get('organization', '')}/{p.get('project', '')})" for p in projects_list]
            idx = 0
            current_id = st.session_state.get(SESSION_CURRENT_PROJECT_ID)
            if current_id:
                for i, p in enumerate(projects_list):
                    if p.get("id") == current_id:
                        idx = i + 1
                        break
            sel = st.selectbox("Progetto salvato", options=options, index=idx, key="sidebar_project_sel")
            if sel and sel != "— Seleziona progetto —":
                proj_idx = options.index(sel) - 1
                proj = projects_list[proj_idx]
                if st.button("Carica progetto", key="sidebar_load"):
                    st.session_state["base_url"] = proj.get("base_url", "")
                    st.session_state["org"] = proj.get("organization", "")
                    st.session_state["project"] = proj.get("project", "")
                    st.session_state["username"] = proj.get("username", "")
                    st.session_state["pat_input"] = proj.get("pat", "")
                    st.session_state[SESSION_CURRENT_PROJECT_ID] = proj.get("id")
                    st.session_state[SESSION_REPOS] = []
                    st.session_state[SESSION_CLIENT] = None
                    st.rerun()
                st.session_state[SESSION_CURRENT_PROJECT_ID] = proj.get("id") if sel != "— Seleziona progetto —" else None

        st.markdown("---")
        st.markdown("**Aggiungi progetto**")
        with st.expander("Nuovo progetto", expanded=False):
            add_name = st.text_input("Nome progetto", key="add_proj_name", placeholder="es. EACS Produzione")
            add_base = st.text_input("Base URL", key="add_proj_base", placeholder="vuoto = cloud")
            add_org = st.text_input("Organization", key="add_proj_org", placeholder="DefaultCollection")
            add_proj = st.text_input("Project", key="add_proj_project", placeholder="EACS")
            add_user = st.text_input("Username (opz.)", key="add_proj_user", placeholder="")
            add_pat = st.text_input("PAT (opz., salvato nel file)", type="password", key="add_proj_pat", placeholder="lascia vuoto per non salvare")
            if st.button("Salva progetto"):
                if add_org and add_proj:
                    new_id = str(uuid.uuid4())[:8]
                    projects_list.append({
                        "id": new_id,
                        "name": add_name or f"{add_org}/{add_proj}",
                        "base_url": add_base.strip(),
                        "organization": add_org.strip(),
                        "project": add_proj.strip(),
                        "username": (add_user or "").strip(),
                        "pat": (add_pat or "").strip(),
                    })
                    save_projects(projects_list)
                    st.success("Progetto aggiunto.")
                    st.rerun()
                else:
                    st.error("Inserisci almeno Organization e Project.")

        if projects_list:
            st.markdown("---")
            st.markdown("**Elimina progetto**")
            del_options = [p.get("id") for p in projects_list]
            def _del_label(pid):
                for p in projects_list:
                    if p.get("id") == pid:
                        return f"{p.get('name', p.get('project', ''))} ({p.get('organization', '')}/{p.get('project', '')})"
                return pid
            to_delete_id = st.selectbox("Scegli da eliminare", options=del_options, format_func=_del_label, key="sidebar_del_sel")
            if st.button("Elimina", key="sidebar_del_btn") and to_delete_id:
                projects_list = [p for p in projects_list if p.get("id") != to_delete_id]
                save_projects(projects_list)
                if st.session_state.get(SESSION_CURRENT_PROJECT_ID) == to_delete_id:
                    st.session_state[SESSION_CURRENT_PROJECT_ID] = None
                st.rerun()

    # ----- Config & connection (compatta) -----
    # Inizializza campi da config solo se non già in session (evita conflitto con "Carica progetto")
    for key, config_key in [
        ("base_url", "base_url"),
        ("org", "organization"),
        ("project", "project"),
        ("username", "username"),
        ("pat_input", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = config.get(config_key, "") if config_key else ""

    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            base_url = st.text_input(
                "Base URL (on‑prem, vuoto = cloud)",
                key="base_url",
                placeholder="http://server:8080/tfs",
            )
        with c2:
            org = st.text_input("Organization", key="org", placeholder="DefaultCollection")
        with c3:
            project = st.text_input("Project", key="project", placeholder="EACS")
        r2_1, r2_2 = st.columns(2)
        with r2_1:
            pat = st.text_input("PAT", type="password", key="pat_input", placeholder="Personal Access Token")
        with r2_2:
            username = st.text_input("Username (opz.)", key="username", placeholder="vuoto per solo PAT")
        @st.fragment(run_every=1 if st.session_state.get("test_conn_ok") else None)
        def _clear_test_ok_after():
            if "test_conn_ok" in st.session_state:
                _, ts = st.session_state["test_conn_ok"]
                if time.time() - ts >= 4:
                    del st.session_state["test_conn_ok"]
                    st.rerun()

        _clear_test_ok_after()

        if st.session_state.get("test_conn_ok"):
            api_ver, ts = st.session_state["test_conn_ok"]
            if time.time() - ts < 4:
                st.success(f"OK · Api {api_ver}")

        btn_1, btn_2 = st.columns(2)
        with btn_1:
            if st.button("Test connessione"):
                if not (org and project and pat):
                    st.error("Inserire Organization, Project e PAT.")
                else:
                    try:
                        client = get_client(org, project, pat, username, base_url)
                        client.test_connection()
                        api_ver = client.discover_git_api_version()
                        st.session_state["test_conn_ok"] = (api_ver, time.time())
                        st.rerun()
                    except AzureDevOpsClientError as e:
                        st.error(f"Errore: {e.message}")
        with btn_2:
            if st.button("Carica repository"):
                if "test_conn_ok" in st.session_state:
                    del st.session_state["test_conn_ok"]
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
    # Inizializza selected da config se prima volta; poi la fonte di verità sono i key dei checkbox
    initial_selected = set(config.get("selected_repo_ids") or [])
    if SESSION_SELECTED_REPOS not in st.session_state:
        st.session_state[SESSION_SELECTED_REPOS] = initial_selected.copy()
    # Costruisci selected_ids dai checkbox in session_state (così "Seleziona tutti" si riflette)
    def _get_selected_ids():
        s = set()
        for r in repos:
            rid = r.get("id") or r.get("name")
            default = rid in (st.session_state.get(SESSION_SELECTED_REPOS) or set()) or rid in initial_selected
            if st.session_state.get(f"repo_{rid}", default):
                s.add(rid)
        return s

    def toggle_all(on: bool):
        for r in repos:
            rid = r.get("id") or r.get("name")
            st.session_state[f"repo_{rid}"] = on
        st.session_state[SESSION_SELECTED_REPOS] = {r.get("id") or r.get("name") for r in repos} if on else set()

    selected_ids = _get_selected_ids()
    st.session_state[SESSION_SELECTED_REPOS] = selected_ids

    sort_options = ["Nome (A→Z)", "Nome (Z→A)"]
    all_col, none_col, spacer, ordina_col = st.columns([1, 1, 3, 1])
    with all_col:
        if st.button("Seleziona tutti"):
            toggle_all(True)
            st.rerun()
    with none_col:
        if st.button("Deseleziona tutti"):
            toggle_all(False)
            st.rerun()
    with ordina_col:
        sort_order = st.selectbox("Ordina", options=sort_options, key="repo_sort")
    repos_sorted = sorted(repos, key=lambda r: (r.get("name") or r.get("id") or "").lower(), reverse=(sort_order == "Nome (Z→A)"))

    # Lista repo in 4 colonne
    N_COLS = 4
    cols = st.columns(N_COLS)
    for i, repo in enumerate(repos_sorted):
        rid = repo.get("id") or repo.get("name")
        name = repo.get("name", rid)
        default_checked = rid in selected_ids
        with cols[i % N_COLS]:
            st.checkbox(name, value=default_checked, key=f"repo_{rid}")
    # Aggiorna selected dopo il render (stato checkbox può essere cambiato dall'utente)
    selected_ids = _get_selected_ids()
    st.session_state[SESSION_SELECTED_REPOS] = selected_ids

    selected_repos = [r for r in repos if (r.get("id") or r.get("name")) in selected_ids]
    if not selected_repos:
        st.warning("Seleziona almeno un repository.")
        st.stop()

    st.divider()
    st.subheader("Definizione ambienti")

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

    dash_title, dash_filter = st.columns([3, 1])
    with dash_title:
        st.subheader("Dashboard risultati")
    with dash_filter:
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
            src_commit = r.get("source_commit") or ""
            tgt_commit = r.get("target_commit") or ""
            source_ref = r.get("source_ref", "")
            target_ref = r.get("target_ref", "")

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

            src_msg = _clean(r.get("source_commit_message") or "")
            src_auth = _clean(r.get("source_commit_author") or "")
            src_date = _fmt_date(r.get("source_commit_date") or "")
            tgt_msg = _clean(r.get("target_commit_message") or "")
            tgt_auth = _clean(r.get("target_commit_author") or "")
            tgt_date = _fmt_date(r.get("target_commit_date") or "")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**SOURCE**")
                if source_ref:
                    st.caption(f"Ref: `{source_ref}`")
                if src_commit:
                    st.caption(f"Commit: `{src_commit}`" + (f" — *{src_auth}*" if src_auth else ""))
                if src_date:
                    st.caption(f"📅 {src_date}")
                st.text(src_msg or "(nessun messaggio)")
            with c2:
                st.markdown("**TARGET**")
                if target_ref:
                    st.caption(f"Ref: `{target_ref}`")
                if tgt_commit:
                    st.caption(f"Commit: `{tgt_commit}`" + (f" — *{tgt_auth}*" if tgt_auth else ""))
                if tgt_date:
                    st.caption(f"📅 {tgt_date}")
                st.text(tgt_msg or "(nessun messaggio)")
            st.divider()
            if r.get("note"):
                st.caption(r["note"])

            commits = r.get("commits") or []
            if commits:
                with st.expander(f"📋 Commit (SOURCE non in TARGET) ({len(commits)})", expanded=False):
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
