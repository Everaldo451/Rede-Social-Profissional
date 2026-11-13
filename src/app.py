from pathlib import Path
import streamlit as st
from streamlit_cookies_controller import CookieController

st.set_page_config(page_title="Rede Social Profissional | TI", page_icon="💻", layout="wide")
st.markdown(f"<style>{(Path(__file__).parent / 'assets' / 'style.css').read_text()}</style>", unsafe_allow_html=True)
from components.auth import render_auth
from components.feed import render_feed
from components.post_form import render_post_form
from components.modules import render_profile, render_network, render_notifications
from components.shared.flash import show_flash
from components.shared.header import render_header
from components.shared.sidebar import render_sidebar
from container import build_container

@st.cache_resource
def get_container(): return build_container()

def current_user(container, cookies):
    token=st.session_state.get("token") or cookies.get("session_token")
    if token:
        st.session_state["token"] = token
    result=container.sessions.resolve(token) if token else None
    if result is None or not result.status or not result.data:
        st.session_state.pop("token",None); return None
    return result.data

try:
    container=get_container()
except Exception as exc:
    st.error(f"Não foi possível conectar aos bancos de dados: {exc}"); st.stop()
cookies=CookieController()
user=current_user(container,cookies)
if user is None:
    render_auth(container,cookies); st.stop()

# Mantém o registro de presença atualizado no Redis durante o uso da aplicação.
container.presence.update_last_seen(user["id"])
filters=render_sidebar(container,user,cookies)
render_header(); st.write(""); show_flash()
feed_tab, profile_tab, network_tab, notifications_tab = st.tabs(["📰 Feed", "👤 Meu perfil", "🤝 Conexões", "🔔 Notificações"])
with feed_tab:
    render_post_form(container,user)
    st.divider()
    render_feed(container,user,filters)
with profile_tab:
    render_profile(container,user)
with network_tab:
    render_network(container,user)
with notifications_tab:
    render_notifications(container,user)
