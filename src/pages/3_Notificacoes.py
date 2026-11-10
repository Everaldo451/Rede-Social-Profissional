import streamlit as st

from controllers.notifications.notification_controller import NotificationController
from repositories.notifications.notification_repository import NotificationRepository
from services.notifications.notification_service import NotificationService

# TODO: trocar por o usuário logado quando o módulo de sessões estiver pronto.
# Por enquanto usamos IDs fixos de teste (ObjectId em string, como no DAS).
USUARIO_ID = "671a2b3c4d5e6f7890123456"
OUTRO_USUARIO_ID = "671a2b3c4d5e6f7890123457"

PAGE_SIZE = 10
MAX_ITEMS = 90  # o DTO de paginação aceita no máximo 100 (buscamos 1 a mais)


@st.cache_resource
def get_controller() -> NotificationController:
    repository = NotificationRepository()
    service = NotificationService(repository)
    return NotificationController(service)


controller = get_controller()

if "notificacoes_limit" not in st.session_state:
    st.session_state.notificacoes_limit = PAGE_SIZE

st.title("Notificações")

# ---------------------------------------------------------------- resumo e ações
unread_response = controller.count_unread_by_user_id(USUARIO_ID)
unread = unread_response.data if unread_response.status else 0

col_unread, col_read_all, col_test = st.columns(3)
col_unread.metric("Não lidas", unread)

if col_read_all.button("Marcar todas como lidas", disabled=unread == 0):
    response = controller.mark_all_as_read(USUARIO_ID)
    if response.status:
        st.rerun()
    st.error(response.message)

if col_test.button("Gerar notificação de teste"):
    response = controller.create(
        {
            "destinatario_id": USUARIO_ID,
            "tipo": "nova_conexao",
            "titulo": "Nova conexão profissional",
            "referencia_tipo": "usuario",
            "referencia_id": OUTRO_USUARIO_ID,
        }
    )
    if response.status:
        st.rerun()
    st.error(response.message)

# ---------------------------------------------------------------------- filtro
mostrar = st.radio("Mostrar", ["Todas", "Não lidas"], horizontal=True)
filters = {"destinatario_id": USUARIO_ID}
if mostrar == "Não lidas":
    filters["lida"] = False

# ----------------------------------------------------------------------- lista
limit = st.session_state.notificacoes_limit
list_response = controller.get_paginated(0, limit + 1, filters)

if not list_response.status:
    st.error(list_response.message)
    st.stop()

notifications = list_response.data
has_more = len(notifications) > limit
notifications = notifications[:limit]

if not notifications:
    st.info("Você não tem notificações.")

for notification in notifications:
    notification_id = notification["_id"]
    lida = notification["lida"]

    with st.container(border=True):
        info, actions = st.columns([4, 1])

        marcador = "⚪" if lida else "🔵"
        info.markdown(f"{marcador} **{notification['titulo']}**")
        criado_em = notification["criado_em"].strftime("%d/%m/%Y %H:%M")
        info.caption(f"{notification['tipo']} · {criado_em} (UTC)")

        if not lida and actions.button(
            "Marcar como lida", key=f"read-{notification_id}"
        ):
            response = controller.update(
                notification_id, {"lida": True}, user_id=USUARIO_ID
            )
            if response.status:
                st.rerun()
            st.error(response.message)

        if actions.button("Excluir", key=f"delete-{notification_id}"):
            response = controller.delete(notification_id, user_id=USUARIO_ID)
            if response.status:
                st.rerun()
            st.error(response.message)

if has_more and limit < MAX_ITEMS:
    if st.button("Ver mais"):
        st.session_state.notificacoes_limit = min(limit + PAGE_SIZE, MAX_ITEMS)
        st.rerun()
