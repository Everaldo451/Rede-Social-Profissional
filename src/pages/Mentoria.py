import logging
from pathlib import Path

import streamlit as st
from neo4j.exceptions import DriverError, Neo4jError
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from components.shared.sidebar import render_sidebar
from controllers.connections.mentorship_controller import MentorshipController
from repositories.connections.mentorship_repository import MentorshipRepository
from repositories.connections.professional_repository import ProfessionalRepository
from repositories.notifications.notification_repository import NotificationRepository
from services.connections.mentorship_service import MentorshipService

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"


def _search_fields(skills, key, label="Nome do mentor"):
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


def _render_profile(profile):
    st.subheader("Perfil profissional")
    st.text(profile["nome"])
    st.caption(
        " · ".join(
            profile[field]
            for field in ("headline", "localizacao", "nivel_carreira")
            if profile.get(field)
        )
    )
    if profile.get("aceita_mentoria"):
        st.success("Disponível para mentoria")

    with st.expander("Habilidades", expanded=True):
        if not profile.get("habilidades"):
            st.caption("Nenhuma habilidade cadastrada.")
        for skill in profile.get("habilidades") or []:
            experience = skill.get("anos_experiencia")
            details = [skill["nome"], skill.get("nivel")]
            if experience is not None:
                details.append(f"{experience} ano(s) de experiência")
            st.text(" · ".join(detail for detail in details if detail))

    sections = (
        ("Experiência profissional", "experiencias", "cargo", "descricao"),
        ("Formação acadêmica", "formacao", "curso", "grau"),
        ("Certificações", "certificacoes", "nome", "url"),
    )
    for label, field, title_field, detail_field in sections:
        with st.expander(label):
            entries = profile.get(field) or []
            if not entries:
                st.caption("Nenhum registro cadastrado.")
            for entry in entries:
                st.text(
                    " · ".join(
                        value
                        for value in (
                            entry.get(title_field),
                            entry.get("organizacao"),
                        )
                        if value
                    )
                )
                if entry.get(detail_field):
                    st.caption(entry[detail_field])


def _render_mentors(controller, user_id, users):
    section = st.radio(
        "Seção de mentoria",
        ("Buscar mentores", "Recomendações", "Solicitações"),
        horizontal=True,
    )
    if section == "Solicitações":
        response = controller.list_requests(user_id)
        if not response.status:
            st.warning(response.message)
            return
        incoming = [
            item
            for item in response.data
            if item["recebida"] and item["status"] == "solicitado"
        ]
        if not incoming:
            st.info("Você não tem solicitações de mentoria pendentes.")
        for item in incoming:
            with st.container(border=True):
                st.text(item["nome"])
                st.caption(f"Habilidade: {item['habilidade_nome']}")
                accept, decline = st.columns(2)
                action = None
                if accept.button("Aceitar", key=f"accept_mentorship_{item['_id']}"):
                    action = "aceitar"
                if decline.button("Recusar", key=f"decline_mentorship_{item['_id']}"):
                    action = "recusar"
                if action:
                    result = controller.update(user_id, item["_id"], {"acao": action})
                    if result.status:
                        st.session_state["mentorship_feedback"] = (
                            "Solicitação de mentoria "
                            f"{'aceita' if action == 'aceitar' else 'recusada'}."
                        )
                        st.rerun()
                    st.warning(result.message)
        return

    if section == "Buscar mentores":
        response = controller.filter_mentors(
            user_id, _search_fields(users.list_skills(), "mentors")
        )
    else:
        desired = controller.desired_skills(user_id).data
        if not desired:
            st.info(
                "O perfil ainda não tem habilidades desejadas para gerar recomendações."
            )
            return
        st.text("Habilidades desejadas: " + ", ".join(desired))
        response = controller.recommend(user_id)

    if not response.status:
        st.warning(response.message)
        return
    if not response.data:
        st.info("Nenhum mentor disponível para esses critérios.")
        return

    mentors = {row["id"]: row for row in response.data}
    skill_names = {
        str(skill["_id"]): skill["nome"]
        for skill in users.list_skills()
    }
    for row in response.data:
        with st.container(border=True):
            st.text(row["perfil"]["nome"])
            st.caption(row["perfil"].get("headline", ""))
            if row.get("habilidades"):
                st.text("Habilidades compatíveis: " + ", ".join(row["habilidades"]))
    mentor_id = st.selectbox(
        "Consultar perfil de mentor",
        list(mentors),
        index=None,
        placeholder="Selecione um mentor",
        format_func=lambda item: mentors[item]["perfil"]["nome"],
        key=f"mentor_profile_{section}",
    )
    if mentor_id:
        response = controller.get_by_user_id(mentor_id)
        if response.status:
            _render_profile(response.data)
        else:
            st.warning(response.message)
        mentor_skills = {
            skill_id: skill_names[skill_id]
            for skill_id in mentors[mentor_id].get("habilidade_ids", [])
            if skill_id in skill_names
        }
        if mentor_skills:
            skill_id = st.selectbox(
                "Habilidade para a mentoria",
                list(mentor_skills),
                format_func=mentor_skills.__getitem__,
                key=f"mentorship_skill_{mentor_id}",
            )
            if st.button(
                "Solicitar mentoria", key=f"request_mentorship_{mentor_id}"
            ):
                result = controller.create(
                    user_id,
                    {"mentor_id": mentor_id, "habilidade_id": skill_id},
                )
                if result.status:
                    st.session_state["mentorship_feedback"] = (
                        "Solicitação de mentoria enviada."
                    )
                    st.rerun()
                st.warning(result.message)
        else:
            st.info("Este mentor não tem habilidades disponíveis para solicitação.")


def _current_user_id():
    from pages.Sessoes import get_authenticated_user_id

    user_id = get_authenticated_user_id()
    if not user_id:
        st.info("Entre na sua conta para acessar a mentoria.")
        st.page_link("pages/Login.py", label="Ir para o login")
        st.stop()
    return user_id


def main():
    st.set_page_config(page_title="Mentoria", layout="wide")
    render_sidebar()
    st.html(THEME)
    user_id = _current_user_id()

    from database import get_mongo_database, get_neo4j_session

    database = get_mongo_database()
    users = ProfessionalRepository(database)
    controller = MentorshipController(
        MentorshipService(
            MentorshipRepository(get_neo4j_session, database),
            users,
            NotificationRepository(),
        )
    )
    st.title("Mentoria")
    feedback = st.session_state.pop("mentorship_feedback", None)
    if feedback:
        st.success(feedback)
    try:
        _render_mentors(controller, user_id, users)
    except (PyMongoError, Neo4jError, DriverError, RedisError):
        logger.exception("Falha ao carregar a página de mentoria.")
        st.error("Não foi possível acessar os dados de mentoria. Tente novamente.")


if __name__ == "__main__":
    main()
