import logging
from pathlib import Path

import streamlit as st
from neo4j.exceptions import DriverError, Neo4jError
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from components.shared.sidebar import render_sidebar
from controllers.connections.connection_controller import ConnectionController
from controllers.connections.mentorship_controller import MentorshipController
from controllers.notifications.notification_controller import NotificationController
from repositories.connections.connection_repository import ConnectionRepository
from repositories.connections.mentorship_repository import MentorshipRepository
from repositories.connections.professional_repository import ProfessionalRepository
from repositories.notifications.notification_repository import NotificationRepository
from services.connections.connection_service import ConnectionService
from services.connections.mentorship_service import MentorshipService
from services.notifications.notification_service import NotificationService

logger = logging.getLogger(__name__)
st.set_page_config(page_title="Notificações", layout="wide")
render_sidebar()
st.html(Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css")

from pages.Sessoes import get_authenticated_user_id

user_id = get_authenticated_user_id()
if not user_id:
    st.info("Entre na sua conta para acessar suas notificações.")
    st.page_link("pages/Login.py", label="Ir para o login")
    st.stop()

PAGE_SIZE = 10
MAX_ITEMS = 90  # o DTO de paginação aceita no máximo 100 (buscamos 1 a mais)


@st.cache_resource
def get_controller() -> NotificationController:
    repository = NotificationRepository()
    service = NotificationService(repository)
    return NotificationController(service)


@st.cache_resource
def get_connection_controller() -> ConnectionController:
    from database import get_mongo_database, get_neo4j_session

    database = get_mongo_database()
    users = ProfessionalRepository(database)
    return ConnectionController(
        ConnectionService(
            ConnectionRepository(get_neo4j_session),
            users,
            NotificationRepository(),
        )
    )


@st.cache_resource
def get_mentorship_controller() -> MentorshipController:
    from database import get_mongo_database, get_neo4j_session

    database = get_mongo_database()
    users = ProfessionalRepository(database)
    return MentorshipController(
        MentorshipService(
            MentorshipRepository(get_neo4j_session, database),
            users,
            NotificationRepository(),
        )
    )


controller = get_controller()


def _mark_notification_as_read(notification_id):
    try:
        response = controller.update(
            notification_id, {"lida": True}, user_id=user_id
        )
    except (PyMongoError, RedisError):
        logger.exception("Falha ao marcar notificação como lida.")
        st.error("Não foi possível atualizar a notificação.")
        return False
    if not response.status:
        st.error(response.message)
        return False
    return True


if "notificacoes_limit" not in st.session_state:
    st.session_state.notificacoes_limit = PAGE_SIZE

st.title("Notificações")

# ---------------------------------------------------------------- resumo e ações
unread_response = controller.count_unread_by_user_id(user_id)
if not unread_response.status:
    st.error(unread_response.message)
    st.stop()
unread = unread_response.data

col_unread, col_read_all, col_test = st.columns(3)
col_unread.metric("Não lidas", unread)

if col_read_all.button("Marcar todas como lidas", disabled=unread == 0):
    response = controller.mark_all_as_read(user_id)
    if response.status:
        st.rerun()
    st.error(response.message)

if col_test.button("Gerar notificação de teste"):
    response = controller.create(
        {
            "destinatario_id": user_id,
            "tipo": "nova_conexao",
            "titulo": "Nova conexão profissional",
            "referencia_tipo": "usuario",
            "referencia_id": user_id,
        }
    )
    if response.status:
        st.rerun()
    st.error(response.message)

# ---------------------------------------------------------------------- filtro
mostrar = st.radio("Mostrar", ["Todas", "Não lidas"], horizontal=True)
filters = {"destinatario_id": user_id}
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

connection_requests = []
mentorship_requests = []
try:
    if any(
        item["tipo"] == "nova_conexao"
        and item.get("referencia_tipo") == "usuario"
        for item in notifications
    ):
        requests_response = get_connection_controller().list_requests(user_id)
        if requests_response.status:
            connection_requests = requests_response.data
        else:
            st.warning(requests_response.message)
    if any(
        item["tipo"] == "mentoria"
        and item.get("referencia_tipo") == "mentoria"
        for item in notifications
    ):
        requests_response = get_mentorship_controller().list_requests(user_id)
        if requests_response.status:
            mentorship_requests = requests_response.data
        else:
            st.warning(requests_response.message)
except (DriverError, Neo4jError, PyMongoError, RedisError):
    logger.exception("Falha ao carregar solicitações vinculadas às notificações.")
    st.error("Não foi possível carregar as solicitações. Tente novamente.")

if not notifications:
    st.info("Você não tem notificações.")

for notification in notifications:
    notification_id = notification["_id"]
    lida = notification["lida"]
    reference_type = notification.get("referencia_tipo")
    reference_id = notification.get("referencia_id")

    with st.container(border=True):
        info, actions = st.columns([4, 1])

        marcador = "⚪" if lida else "🔵"
        info.markdown(f"{marcador} **{notification['titulo']}**")
        criado_em = notification["criado_em"].strftime("%d/%m/%Y %H:%M")
        info.caption(f"{notification['tipo']} · {criado_em} (UTC)")

        if (
            notification["tipo"] == "nova_conexao"
            and reference_type == "usuario"
        ):
            request = next(
                (
                    item
                    for item in connection_requests
                    if item["recebida"]
                    and item["status"] == "pendente"
                    and item["remetente_id"] == reference_id
                ),
                None,
            )
            if request:
                st.caption("Solicitação de conexão")
                accept, decline = st.columns(2)
                action = None
                if accept.button(
                    "Aceitar", key=f"accept_connection_{notification_id}"
                ):
                    action = "aceitar"
                if decline.button(
                    "Recusar", key=f"decline_connection_{notification_id}"
                ):
                    action = "recusar"
                if action:
                    try:
                        response = (
                            get_connection_controller().update_connection_request(
                                user_id,
                                request["remetente_id"],
                                {"solicitacao_id": request["id"], "acao": action},
                            )
                        )
                    except (DriverError, Neo4jError, PyMongoError, RedisError):
                        logger.exception("Falha ao responder à solicitação de conexão.")
                        st.error("Não foi possível responder à solicitação.")
                    else:
                        if response.status:
                            if _mark_notification_as_read(notification_id):
                                st.rerun()
                            st.success("Solicitação de conexão respondida.")
                        else:
                            st.error(response.message)

        if (
            notification["tipo"] == "mentoria"
            and reference_type == "mentoria"
        ):
            request = next(
                (
                    item
                    for item in mentorship_requests
                    if item["recebida"]
                    and item["status"] == "solicitado"
                    and item["_id"] == reference_id
                ),
                None,
            )
            if request:
                st.caption(
                    f"Solicitação de {request['nome']} · "
                    f"{request['habilidade_nome']}"
                )
                accept, decline = st.columns(2)
                action = None
                if accept.button(
                    "Aceitar", key=f"accept_mentorship_{notification_id}"
                ):
                    action = "aceitar"
                if decline.button(
                    "Recusar", key=f"decline_mentorship_{notification_id}"
                ):
                    action = "recusar"
                if action:
                    try:
                        response = get_mentorship_controller().update(
                            user_id,
                            reference_id,
                            {"acao": action},
                        )
                    except (DriverError, Neo4jError, PyMongoError, RedisError):
                        logger.exception("Falha ao responder à solicitação de mentoria.")
                        st.error("Não foi possível responder à solicitação.")
                    else:
                        if response.status:
                            if _mark_notification_as_read(notification_id):
                                st.rerun()
                            st.success("Solicitação de mentoria respondida.")
                        else:
                            st.error(response.message)

        if not lida and actions.button(
            "Marcar como lida", key=f"read-{notification_id}"
        ):
            if _mark_notification_as_read(notification_id):
                st.rerun()

        if actions.button("Excluir", key=f"delete-{notification_id}"):
            response = controller.delete(notification_id, user_id=user_id)
            if response.status:
                st.rerun()
            st.error(response.message)

if has_more and limit < MAX_ITEMS:
    if st.button("Ver mais"):
        st.session_state.notificacoes_limit = min(limit + PAGE_SIZE, MAX_ITEMS)
        st.rerun()
