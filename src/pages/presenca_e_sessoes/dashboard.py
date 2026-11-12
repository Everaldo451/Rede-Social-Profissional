from datetime import datetime, timezone
from html import escape
from pathlib import Path

import streamlit as st


ASSETS = Path(__file__).resolve().parents[2] / "assets" / "dashboard"


def request_logout():
    st.session_state["logout_requested"] = True


def revoke_session(sessions, session, reference):
    result = sessions.revoke_other_session({**session, "reference": reference})
    st.session_state["session_revocation"] = result


@st.fragment(run_every=20)
def render_panels(sessions, session, users, presence):
    viewer = sessions.get_current_user(session)
    if not viewer.status:
        st.rerun()

    with st.container(key="presence_panel"):
        heading, action = st.columns([4, 1.5], vertical_alignment="center")
        with heading:
            st.subheader("Presença online")
        with action:
            refresh = st.button("Atualizar presença")
        professionals = users.list_presence_profiles(viewer.data)
        online = presence.get_online_users(
            session, [user["user_id"] for user in professionals], activity=refresh
        )
        if not online.status:
            st.rerun()
        for user in professionals:
            status = "Online" if user["user_id"] in online.data else "Offline"
            st.html(
                f'<div class="presence-row"><span>{escape(user["name"])}</span>'
                f'<span class="presence-badge {status.lower()}">{status}</span></div>'
            )
        if not professionals:
            st.caption("Nenhum outro profissional cadastrado.")

    with st.container(key="sessions_panel"):
        st.subheader("Gerenciamento de sessões")
        active = sessions.get_all_sessions_for_current_user(session)
        if active.status:
            st.metric("Sessões ativas", len(active.data))
            result = st.session_state.pop("session_revocation", None)
            if result is not None:
                if result.status:
                    st.success(result.message)
                else:
                    st.error(result.message)

            for entry in sorted(active.data, key=lambda item: (not item["current"], item["reference"])):
                reference = entry["reference"]
                label = "Sessão atual" if entry["current"] else f"Sessão {reference[:10]}"
                created_at = entry["created_at"]
                if created_at is not None:
                    started = datetime.fromtimestamp(created_at, timezone.utc)
                    label += f" · Iniciada em {started:%d/%m/%Y às %H:%M:%S} UTC"
                details, action = st.columns([3, 2])
                details.write(label)
                if not entry["current"]:
                    action.button(
                        "Encerrar sessão",
                        key=f"revoke_{reference}",
                        on_click=revoke_session,
                        args=(sessions, session, reference),
                    )


def render_dashboard(sessions, session, users, presence):
    st.html(ASSETS / "dashboard.css")
    with st.container(key="dashboard_shell"):
        with st.container(key="dashboard_header"):
            title, account = st.columns([4, 1], vertical_alignment="center")
            with title:
                st.html('<div class="dashboard-eyebrow">Painel de presença</div>')
                st.title("Rede Social Profissional")
            with account:
                st.button("Sair", on_click=request_logout)
        render_panels(sessions, session, users, presence)
