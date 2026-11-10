from datetime import datetime, timezone
from html import escape
from pathlib import Path

import streamlit as st
from streamlit_cookies_controller import CookieController

from controllers.sessions.online_presence_controller import OnlinePresenceController
from controllers.sessions.session_controller import SessionController
from repositories.profile.user_repository import UserRepository
from repositories.sessions.online_presence_repository import OnlinePresenceRepository
from repositories.sessions.session_repository import SessionRepository
from services.profile.user_service import UserService
from services.sessions.online_presence_service import OnlinePresenceService
from services.sessions.session_service import SessionService


COOKIE_NAME = "rede_social_session"
ASSETS = Path(__file__).resolve().parent / "assets"
st.set_page_config(page_title="Rede Social Profissional", layout="wide")
session_repository = SessionRepository()
users = UserService(UserRepository())
presence_service = OnlinePresenceService(OnlinePresenceRepository(), session_repository.ttl)
sessions = SessionController(
    SessionService(session_repository, users, presence_service)
)
presence = OnlinePresenceController(presence_service)

cookie_cache_key = "session_cookie_cache"
if cookie_cache_key not in st.session_state:
    st.session_state[cookie_cache_key] = dict(st.context.cookies)
cookies = CookieController(key=cookie_cache_key)
secure_cookie = (st.context.url or "").startswith("https://")
session_id = cookies.get(COOKIE_NAME)
session = {"session_id": session_id}
current = sessions.get_current_user(session)

logout_requested = st.session_state.pop("logout_requested", False)
if logout_requested:
    sessions.logout(session)
    if cookies.get(COOKIE_NAME):
        cookies.remove(COOKIE_NAME, secure=secure_cookie)

if logout_requested or not current.status:
    login_area = st.empty()
    with login_area.container():
        st.html(ASSETS / "login.css")
        if logout_requested:
            st.html('<p class="login-notice" role="status">Sessão encerrada.</p>')
        with st.container(key="login_card"):
            illustration, credentials = st.columns([1.25, 1], gap=None)
            with illustration:
                st.image(str(ASSETS / "login.png"), width="stretch")
            with credentials:
                with st.container(key="login_credentials"):
                    st.html("""
                        <div class="login-brand">Rede Social Profissional</div>
                        <h1 class="login-heading">Olá,<br>boas-vindas!</h1>
                        <p class="login-copy">Entre na sua conta para acessar sua rede.</p>
                    """)
                    with st.form("login", clear_on_submit=True, border=False):
                        email = st.text_input("E-mail", placeholder="voce@exemplo.com")
                        password = st.text_input("Senha", type="password")
                        submitted = st.form_submit_button("Entrar", width="stretch")
                    login_feedback = st.empty()
    if submitted:
        result = sessions.login({"email": email, "password": password})
        if not result.status:
            login_feedback.error(result.message)
            st.stop()
        cookies.set(COOKIE_NAME, result.data, secure=secure_cookie)
        session = {"session_id": result.data}
        current = sessions.get_current_user(session)
        login_area.empty()
    else:
        st.stop()

def request_logout():
    st.session_state["logout_requested"] = True


def revoke_session(reference):
    result = sessions.revoke_other_session({**session, "reference": reference})
    st.session_state["session_revocation"] = result


@st.fragment(run_every=20)
def dashboard():
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
                        args=(reference,),
                    )


st.html(ASSETS / "dashboard.css")
with st.container(key="dashboard_shell"):
    with st.container(key="dashboard_header"):
        title, account = st.columns([4, 1], vertical_alignment="center")
        with title:
            st.html('<div class="dashboard-eyebrow">Painel de presença</div>')
            st.title("Rede Social Profissional")
        with account:
            st.button("Sair", on_click=request_logout)
    dashboard()
