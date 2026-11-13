import logging
from pathlib import Path

import streamlit as st
from neo4j.exceptions import DriverError, Neo4jError
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from controllers.connections.connection_controller import ConnectionController
from repositories.connections.connection_repository import ConnectionRepository
from repositories.connections.professional_repository import ProfessionalRepository
from repositories.notifications.notification_repository import NotificationRepository
from services.connections.connection_service import ConnectionService

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"


def _search_fields(skills, key, label="Nome do profissional"):
    skill_names = {str(skill["_id"]): skill["nome"] for skill in skills}
    name = st.text_input(label, max_chars=100, key=f"{key}_name")
    skill_id = st.selectbox(
        "Habilidade",
        list(skill_names),
        index=None,
        placeholder="Todas as habilidades",
        format_func=skill_names.__getitem__,
        key=f"{key}_skill",
    )
    return {"nome": name, "habilidade_id": skill_id}


def _professionals(controller, user_id, users):
    filters = _search_fields(users.list_skills(), "professionals")
    response = controller.search_professionals(user_id, filters)
    if not response.status:
        st.warning(response.message)
        return
    if not response.data:
        st.info("Nenhum profissional encontrado com esses filtros.")
        return
    for profile in response.data:
        other_id = str(profile["_id"])
        with st.container(border=True):
            st.text(profile["nome"])
            st.caption(profile.get("headline", ""))
            if st.button("Enviar solicitação", key=f"request_{other_id}"):
                sent = controller.request_connection(user_id, other_id)
                if sent.status:
                    st.success("Solicitação enviada.")
                else:
                    st.warning(sent.message)


def _requests(controller, user_id):
    response = controller.list_requests(user_id)
    if not response.status:
        st.warning(response.message)
        return
    for label, received in (("Recebidas", True), ("Enviadas", False)):
        st.subheader(label)
        requests = [row for row in response.data if row["recebida"] == received]
        if not requests:
            st.caption("Nenhuma solicitação.")
        for row in requests:
            with st.container(border=True):
                st.text(row["nome"])
                st.caption(f"Status: {row['status'].capitalize()}")
                if not received or row["status"] != "pendente":
                    continue
                accept, decline = st.columns(2)
                action = None
                if accept.button("Aceitar", key=f"accept_{row['id']}"):
                    action = "aceitar"
                if decline.button("Recusar", key=f"decline_{row['id']}"):
                    action = "recusar"
                if action:
                    decision = controller.update_connection_request(
                        user_id,
                        row["remetente_id"],
                        {"solicitacao_id": row["id"], "acao": action},
                    )
                    if decision.status:
                        st.session_state["network_feedback"] = (
                            f"Solicitação {decision.data}."
                        )
                        st.rerun()
                    st.warning(decision.message)


def _connections(controller, user_id):
    total = controller.count_connections(user_id).data
    st.metric("Conexões diretas", total)
    if not total:
        st.info("Sua rede ainda não tem conexões.")
        return
    page_size = 10
    pages = (total + page_size - 1) // page_size
    page = st.number_input("Página", 1, pages, 1) if pages > 1 else 1
    response = controller.get_paginated_for_user(
        user_id, (page - 1) * page_size, page_size
    )
    for profile in response.data:
        with st.container(border=True):
            st.text(profile["nome"])
            st.caption(profile.get("headline", ""))


def _degrees(controller, user_id):
    st.subheader("Menor caminho entre profissionais")
    st.caption("O cálculo considera somente conexões aceitas.")
    name = st.text_input("Filtrar por nome", max_chars=100, key="path_name")
    response = controller.search_professionals(user_id, {"nome": name})
    people = {str(item["_id"]): item["nome"] for item in response.data}
    if not people:
        st.info("Nenhum profissional encontrado.")
        return
    target = st.selectbox(
        "Profissional de destino",
        list(people),
        index=None,
        placeholder="Selecione um profissional",
        format_func=people.__getitem__,
    )
    if st.button("Calcular menor caminho", disabled=target is None):
        path = controller.get_shortest_path(user_id, target)
        if not path.status:
            st.warning(path.message)
        elif path.data is None:
            st.info("Não há um caminho de conexões entre vocês.")
        else:
            st.metric("Graus de separação", path.data["graus"])
            st.text(" → ".join(path.data["nomes"]))


def _render_network(controller, user_id, users):
    st.title("Rede de Conexões Profissionais")
    feedback = st.session_state.pop("network_feedback", None)
    if feedback:
        st.success(feedback)
    section = st.radio(
        "Seção da rede",
        ("Buscar profissionais", "Solicitações", "Minhas conexões", "Graus de separação"),
        horizontal=True,
    )
    if section == "Buscar profissionais":
        _professionals(controller, user_id, users)
    elif section == "Solicitações":
        _requests(controller, user_id)
    elif section == "Minhas conexões":
        _connections(controller, user_id)
    else:
        _degrees(controller, user_id)


def _current_user_id():
    from pages.Sessoes import get_authenticated_user_id

    user_id = get_authenticated_user_id()
    if not user_id:
        st.info("Entre na sua conta para acessar sua rede.")
        st.page_link("pages/Login.py", label="Ir para o login")
        st.stop()
    return user_id


def main():
    st.set_page_config(page_title="Rede de conexões", layout="wide")
    st.html(THEME)
    user_id = _current_user_id()

    from database import get_mongo_database, get_neo4j_session

    users = ProfessionalRepository(get_mongo_database())
    controller = ConnectionController(
        ConnectionService(
            ConnectionRepository(get_neo4j_session),
            users,
            NotificationRepository(),
        )
    )
    try:
        _render_network(controller, user_id, users)
    except (PyMongoError, Neo4jError, DriverError, RedisError):
        logger.exception("Falha ao carregar a rede de conexões.")
        st.error("Não foi possível acessar os dados da rede. Tente novamente.")


if __name__ == "__main__":
    main()
