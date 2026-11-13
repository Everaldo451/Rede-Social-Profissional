from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import streamlit as st
from streamlit_cookies_controller import CookieController

from components.shared.sidebar import render_sidebar
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


def revoke_session(sessions, session, reference):
    result = sessions.revoke_other_session({**session, "reference": reference})
    st.session_state["session_revocation"] = result


def render_sessions(sessions, session):
    viewer = sessions.get_current_user(session)
    if not viewer.status:
        st.rerun()

    with st.container(key="sessions_panel"):
        st.subheader("Suas sessões")
        st.caption(
            "Confira os acessos ativos à sua conta e encerre sessões que não reconhece."
        )
        active = sessions.get_all_sessions_for_current_user(session)
        if not active.status:
            st.error(active.message)
            return

        st.metric("Sessões ativas", len(active.data))
        result = st.session_state.pop("session_revocation", None)
        if result is not None:
            if result.status:
                st.success(result.message)
            else:
                st.error(result.message)

        if not active.data:
            st.info("Não há sessões ativas para exibir.")
            return

        for entry in sorted(
            active.data, key=lambda item: (not item["current"], item["reference"])
        ):
            reference = entry["reference"]
            created_at = entry["created_at"]
            with st.container(border=True):
                details, action = st.columns([4, 1.5], vertical_alignment="center")
                details.markdown(
                    "**Esta sessão**" if entry["current"] else "**Outro dispositivo**"
                )
                details.caption(f"Identificador: {reference[:10]}")
                if created_at is not None:
                    started = datetime.fromtimestamp(created_at, timezone.utc)
                    details.caption(f"Iniciada em {started:%d/%m/%Y às %H:%M} UTC")
                if not entry["current"]:
                    action.button(
                        "Encerrar sessão",
                        key=f"revoke_{reference}",
                        on_click=revoke_session,
                        args=(sessions, session, reference),
                    )


def render_dashboard(sessions, session):
    st.html(THEME)
    st.html(ASSETS / "dashboard.css")
    with st.container(key="sessions_shell"):
        with st.container(key="dashboard_header"):
            st.html('<div class="dashboard-eyebrow">Segurança da conta</div>')
            st.title("Gerenciamento de sessões")
        render_sessions(sessions, session)


def render_page():
    st.set_page_config(page_title="Sessões", layout="wide")
    render_sidebar()
    sessions, _, _ = build_runtime()
    cookies = get_cookie_controller()
    session = {"session_id": cookies.get(COOKIE_NAME)}

    if not sessions.get_current_user(session).status:
        st.info("Entre na sua conta para acessar as sessões.")
        st.page_link("pages/Login.py", label="Ir para o login")
        return

    render_dashboard(sessions, session)


if __name__ == "__main__":
    render_page()
