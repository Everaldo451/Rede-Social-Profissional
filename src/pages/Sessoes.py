from datetime import datetime, timezone
from html import escape
from pathlib import Path
from types import SimpleNamespace

import streamlit as st
from streamlit_cookies_controller import CookieController

from common.errors import UnauthorizedError
from controllers.sessions.online_presence_controller import OnlinePresenceController
from controllers.sessions.session_controller import SessionController
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository
from repositories.sessions.online_presence_repository import OnlinePresenceRepository
from repositories.sessions.session_repository import SessionRepository
from services.profile.user_service import UserService
from services.sessions.online_presence_service import OnlinePresenceService
from services.sessions.session_service import SessionService


ASSETS = Path(__file__).resolve().parents[1] / "assets" / "dashboard"
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"
COOKIE_NAME = "rede_social_session"


def build_runtime():
    session_repository = SessionRepository()
    users = UserService(
        UserRepository(),
        UserSkillRepository(),
        UserOrganizationsRepository(),
    )
    presence_service = OnlinePresenceService(
        OnlinePresenceRepository(), session_repository.ttl
    )

    def authenticate_user(email, password):
        try:
            user = users.authenticate(email, password)
        except UnauthorizedError:
            return None
        return user["usuario_id"]

    session_users = SimpleNamespace(authenticate=authenticate_user)
    sessions = SessionController(
        SessionService(session_repository, session_users, presence_service)
    )
    presence = OnlinePresenceController(presence_service)
    return sessions, users, presence


def get_cookie_controller():
    cookie_cache_key = "session_cookie_cache"
    if cookie_cache_key not in st.session_state:
        st.session_state[cookie_cache_key] = dict(st.context.cookies)
    return CookieController(key=cookie_cache_key)


def get_authenticated_user_id():
    session_id = get_cookie_controller().get(COOKIE_NAME)
    if not session_id:
        return None

    sessions, _, _ = build_runtime()
    response = sessions.get_current_user({"session_id": session_id})
    return response.data if response.status else None


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
        professionals = [
            {"user_id": profile["usuario_id"], "name": profile["nome"]}
            for profile in users.list_all()
            if profile.get("usuario_id") != viewer.data
        ]
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
    st.html(THEME)
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


def render_page():
    st.set_page_config(page_title="Sessões", layout="wide")
    sessions, users, presence = build_runtime()
    cookies = get_cookie_controller()
    session = {"session_id": cookies.get(COOKIE_NAME)}
    logout_requested = st.session_state.pop("logout_requested", False)

    if logout_requested:
        sessions.logout(session)
        if session["session_id"]:
            cookies.remove(
                COOKIE_NAME,
                secure=(st.context.url or "").startswith("https://"),
            )
        st.switch_page("pages/Login.py")
        return

    if not sessions.get_current_user(session).status:
        st.info("Entre na sua conta para acessar as sessões.")
        st.page_link("pages/Login.py", label="Ir para o login")
        return

    render_dashboard(sessions, session, users, presence)


if __name__ == "__main__":
    render_page()
