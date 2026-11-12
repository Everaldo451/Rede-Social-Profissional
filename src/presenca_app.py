import streamlit as st
from streamlit_cookies_controller import CookieController

from controllers.sessions.online_presence_controller import OnlinePresenceController
from controllers.sessions.session_controller import SessionController
from pages.presenca_e_sessoes.dashboard import render_dashboard
from pages.presenca_e_sessoes.login import render_login
from repositories.profile.user_repository import UserRepository
from repositories.sessions.online_presence_repository import OnlinePresenceRepository
from repositories.sessions.session_repository import SessionRepository
from services.profile.user_service import UserService
from services.sessions.online_presence_service import OnlinePresenceService
from services.sessions.session_service import SessionService


COOKIE_NAME = "rede_social_session"


def render_app():
    session_repository = SessionRepository()
    users = UserService(UserRepository())
    presence_service = OnlinePresenceService(OnlinePresenceRepository(), session_repository.ttl)
    sessions = SessionController(SessionService(session_repository, users, presence_service))
    presence = OnlinePresenceController(presence_service)

    cookie_cache_key = "session_cookie_cache"
    if cookie_cache_key not in st.session_state:
        st.session_state[cookie_cache_key] = dict(st.context.cookies)
    cookies = CookieController(key=cookie_cache_key)
    secure_cookie = (st.context.url or "").startswith("https://")
    session = {"session_id": cookies.get(COOKIE_NAME)}

    logout_requested = st.session_state.pop("logout_requested", False)
    if logout_requested:
        sessions.logout(session)
        if cookies.get(COOKIE_NAME):
            cookies.remove(COOKIE_NAME, secure=secure_cookie)

    if logout_requested or not sessions.get_current_user(session).status:
        session_id = render_login(sessions, logout_requested=logout_requested)
        if session_id is None:
            return
        cookies.set(COOKIE_NAME, session_id, secure=secure_cookie)
        session = {"session_id": session_id}

    render_dashboard(sessions, session, users, presence)


st.set_page_config(page_title="Rede Social Profissional", layout="wide")
st.navigation([st.Page(render_app, title="Rede Social Profissional")], position="hidden").run()
