import logging
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError
from pymongo.errors import PyMongoError
from redis.exceptions import RedisError

from common.choices import DEGREES, SKILL_LEVELS, SKILL_TYPES
from controllers.connections.connection_controller import ConnectionController
from controllers.shared.media_controller import MediaController
from controllers.profile.user_controller import UserController
from dto.profile.request.user_requests import UserIdRequest
from repositories.profile.organization_repository import OrganizationRepository
from repositories.profile.skill_repository import SkillRepository
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository
from repositories.connections.connection_repository import ConnectionRepository
from repositories.connections.professional_repository import ProfessionalRepository
from repositories.notifications.notification_repository import NotificationRepository
from repositories.shared.media_repository import MediaRepository
from services.connections.connection_service import ConnectionService
from services.profile.user_service import UserService
from services.shared.media_service import MediaService

logger = logging.getLogger(__name__)
THEME = Path(__file__).resolve().parents[1] / "assets" / "shared" / "page_theme.css"

SKILL_RELATION_LABELS = {
    "has": "Possui habilidade",
    "wants": "Deseja desenvolver",
    "teaches": "Ensina",
}
ORGANIZATION_RELATION_LABELS = {
    "TRABALHOU_EM": "Trabalhou em",
    "ESTUDOU_EM": "Estudou em",
    "MEMBRO_DE": "Membro de",
}
SKILL_TYPE_LABELS = {
    "has": "Possui",
    "wants": "Quer desenvolver",
    "teaches": "Ensina",
}


def _format_date(value, missing="Não informado"):
    if value is None:
        return missing
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
                "%d/%m/%Y"
            )
        except ValueError:
            return value
    return str(value)


def _organization_name(organization_repository, organization_id, cache):
    if not organization_id:
        return "Organização não informada"
    organization_id = str(organization_id)
    if organization_id not in cache:
        cache[organization_id] = organization_repository.get_by_id(organization_id)
    organization = cache[organization_id]
    return organization.get("nome") if organization else "Organização não encontrada"


def _render_experiences(
    user,
    organization_repository,
    organization_cache,
    user_id=None,
    user_controller=None,
):
    st.subheader("Experiência profissional")
    experiences = user.get("experiencias") or []
    if not experiences:
        st.caption("Nenhuma experiência informada.")
        return

    for index, experience in enumerate(experiences):
        organization_name = _organization_name(
            organization_repository,
            experience.get("organizacao_id"),
            organization_cache,
        )
        details, action = (
            st.columns([5, 1]) if user_controller else (st.container(), None)
        )
        with details:
            st.markdown(
                f"**{experience.get('cargo', 'Cargo não informado')} — "
                f"{organization_name}**"
            )
        start = _format_date(experience.get("data_inicio"))
        end = (
            "Atual"
            if experience.get("atual")
            else _format_date(experience.get("data_fim"))
        )
        st.write(f"{start} – {end}")
        if experience.get("descricao"):
            st.write(experience["descricao"])
        organization_id = experience.get("organizacao_id")
        if user_controller and organization_id:
            with action:
                if st.button("Remover", key=f"remove_experience_{index}"):
                    _handle_profile_response(
                        user_controller.remove_experience(
                            user_id,
                            str(organization_id),
                            experience.get("cargo", ""),
                            experience.get("data_inicio"),
                        )
                    )


def _render_education(
    user,
    organization_repository,
    organization_cache,
    user_id=None,
    user_controller=None,
):
    st.subheader("Formação")
    education_entries = user.get("formacao") or []
    if not education_entries:
        st.caption("Nenhuma formação informada.")
        return

    for index, education in enumerate(education_entries):
        institution_name = _organization_name(
            organization_repository,
            education.get("instituicao_id"),
            organization_cache,
        )
        details_column, action = (
            st.columns([5, 1]) if user_controller else (st.container(), None)
        )
        with details_column:
            st.markdown(
                f"**{education.get('curso', 'Curso não informado')} — "
                f"{institution_name}**"
            )
        details = [education["grau"]] if education.get("grau") else []
        years = " – ".join(
            str(year)
            for year in (
                education.get("ano_inicio"),
                education.get("ano_conclusao") or "Atual",
            )
            if year
        )
        if years:
            details.append(years)
        st.write(" · ".join(details))
        institution_id = education.get("instituicao_id")
        if user_controller and institution_id:
            with action:
                if st.button("Remover", key=f"remove_education_{index}"):
                    _handle_profile_response(
                        user_controller.remove_education(
                            user_id,
                            str(institution_id),
                            education.get("curso", ""),
                            education.get("grau", ""),
                        )
                    )


def _render_skills(
    user_id,
    user_skill_repository,
    skill_repository,
    user_controller=None,
):
    st.subheader("Habilidades")
    relationships = user_skill_repository.get_skills({"usuario_id": user_id})
    if not relationships:
        st.caption("Nenhuma habilidade informada.")
        return

    for index, relationship in enumerate(relationships):
        skill = skill_repository.get_by_id(relationship["habilidade_id"])
        skill_name = skill.get("nome") if skill else "Habilidade não encontrada"
        relation_label = SKILL_RELATION_LABELS.get(
            relationship.get("tipo"), relationship.get("tipo", "Habilidade")
        )
        details = [relation_label]
        if relationship.get("nivel"):
            details.append(f"Nível: {relationship['nivel']}")
        if relationship.get("experiencia_anos") is not None:
            details.append(
                f"Experiência: {relationship['experiencia_anos']} anos"
            )
        if relationship.get("modalidade"):
            details.append(f"Modalidade: {relationship['modalidade']}")
        if relationship.get("disponibilidade"):
            details.append(
                f"Disponibilidade: {relationship['disponibilidade']}"
            )
        skill_column, action = (
            st.columns([5, 1]) if user_controller else (st.container(), None)
        )
        with skill_column:
            st.markdown(f"**{skill_name}**")
            st.write(" · ".join(details))
        if user_controller:
            with action:
                if st.button("Remover", key=f"remove_skill_{index}"):
                    _handle_profile_response(
                        user_controller.remove_skill(
                            user_id,
                            relationship["habilidade_id"],
                            relationship["tipo"],
                        )
                    )


def _render_organization_relationships(
    organization_repository,
    organization_cache,
    relationships,
    user_id=None,
    user_controller=None,
):
    st.subheader("Relacionamentos com organizações")
    if not relationships:
        st.caption("Nenhum relacionamento com organização informado.")
        return

    for index, relationship in enumerate(relationships):
        organization_name = _organization_name(
            organization_repository,
            relationship.get("organizacao_id"),
            organization_cache,
        )
        relationship_type = ORGANIZATION_RELATION_LABELS.get(
            relationship.get("tipo"),
            relationship.get("tipo", "").replace("_", " ").title(),
        )
        st.markdown(f"**{relationship_type} — {organization_name}**")
        details = []
        for field in (
            "cargo",
            "curso",
            "grau",
            "papel",
            "status",
            "data_inicio",
            "data_fim",
            "ano_inicio",
            "ano_conclusao",
            "desde",
        ):
            value = relationship.get(field)
            if value is not None:
                if field in {"data_inicio", "data_fim", "desde"}:
                    value = _format_date(value)
                details.append(f"{field.replace('_', ' ').title()}: {value}")
        if relationship.get("atual") is True:
            details.append("Atual")
        if details:
            st.write(" · ".join(details))
        if (
            user_controller
            and relationship.get("tipo") == "MEMBRO_DE"
            and relationship.get("papel")
        ):
            if st.button(
                "Remover vínculo",
                key=f"remove_membership_{index}",
            ):
                _handle_profile_response(
                    user_controller.remove_membership(
                        user_id,
                        str(relationship["organizacao_id"]),
                        relationship["papel"],
                    )
                )


def _render_organizations(
    user,
    relationships,
    organization_repository,
    organization_cache,
):
    organization_ids = {
        str(organization_id)
        for field in ("experiencias", "formacao", "certificacoes")
        for record in user.get(field) or []
        for organization_id in (
            record.get("organizacao_id")
            or record.get("instituicao_id")
            or record.get("emissor_id"),
        )
        if organization_id
    }
    organization_ids.update(
        str(relationship["organizacao_id"])
        for relationship in relationships
        if relationship.get("organizacao_id")
    )
    if not organization_ids:
        return

    st.subheader("Organizações")
    for organization_id in sorted(organization_ids):
        organization = organization_cache.get(organization_id)
        if organization is None:
            organization = organization_repository.get_by_id(organization_id)
            organization_cache[organization_id] = organization
        if organization is None:
            continue

        st.markdown(f"**{organization.get('nome', 'Organização')}**")
        details = []
        if organization.get("setor"):
            details.append(organization["setor"])
        location = ", ".join(
            value
            for value in (organization.get("cidade"), organization.get("estado"))
            if value
        )
        if location:
            details.append(location)
        if organization.get("tipos"):
            details.append(", ".join(organization["tipos"]))
        if organization.get("status_verificacao"):
            details.append(
                f"Verificação: {organization['status_verificacao']}"
            )
        if details:
            st.write(" · ".join(details))
        if organization.get("site"):
            st.write(organization["site"])


def _render_certifications(user, organization_repository, organization_cache):
    certifications = user.get("certificacoes") or []
    if not certifications:
        return

    st.subheader("Certificações")
    for certification in certifications:
        issuer = _organization_name(
            organization_repository,
            certification.get("emissor_id"),
            organization_cache,
        )
        st.markdown(f"**{certification.get('nome', 'Certificação')} — {issuer}**")
        if certification.get("data_emissao"):
            st.write(f"Emitida em {_format_date(certification['data_emissao'])}")
        if certification.get("url"):
            st.write(certification["url"])


def _handle_profile_response(response):
    if not response.status:
        st.error(response.message)
        return
    st.session_state["profile_feedback"] = response.message or "Alterações salvas."
    st.rerun()


def _render_profile_identity(user, user_id, viewer_id):
    media_controller = MediaController(MediaService(MediaRepository()))
    media_response = media_controller.get_one(
        {
            "proprietario_id": user_id,
            "proprietario_tipo": "usuario",
            "tipo": "imagem_perfil",
            "visibilidade": "publica",
        }
    )
    photo, details, action = st.columns([1, 4, 1.5], vertical_alignment="center")
    if media_response.status:
        photo.image(media_response.data["content"], width=150)
    elif media_response.message != "Mídia não encontrada.":
        photo.caption("Foto indisponível")

    details.header(user.get("nome", "Perfil sem nome"))
    profile_details = [
        user.get("headline"),
        user.get("localizacao"),
        user.get("nivel_carreira"),
    ]
    details.write(" · ".join(value for value in profile_details if value) or " ")

    if viewer_id and str(viewer_id) != user_id:
        from database import get_mongo_database, get_neo4j_session

        database = get_mongo_database()
        users = ProfessionalRepository(database)
        controller = ConnectionController(
            ConnectionService(
                ConnectionRepository(get_neo4j_session),
                users,
                NotificationRepository(),
            )
        )
        if action.button("Conectar", type="primary"):
            response = controller.request_connection(viewer_id, user_id)
            if response.status:
                st.success("Solicitação de conexão enviada.")
            else:
                st.warning(response.message)


def _render_profile_editor(
    user_id,
    user,
    user_controller,
    skill_repository,
    organization_repository,
):
    st.subheader("Editar meu perfil")
    with st.expander("Dados profissionais", expanded=True):
        with st.form("profile_edit_form"):
            name = st.text_input("Nome completo", value=user.get("nome") or "")
            headline = st.text_input(
                "Título profissional", value=user.get("headline") or ""
            )
            location = st.text_input(
                "Localização", value=user.get("localizacao") or ""
            )
            summary = st.text_area(
                "Resumo profissional", value=user.get("resumo") or ""
            )
            submitted = st.form_submit_button("Salvar perfil", type="primary")
        if submitted:
            _handle_profile_response(
                user_controller.update(
                    user_id,
                    {
                        "nome": name,
                        "headline": headline,
                        "localizacao": location,
                        "resumo": summary,
                    },
                )
            )

    with st.expander("Adicionar habilidade"):
        skills = skill_repository.get_paginated(0, 100)
        if not skills:
            st.info("Ainda não há habilidades disponíveis para adicionar.")
        else:
            skill_names = {str(skill["_id"]): skill["nome"] for skill in skills}
            with st.form("add_skill_form"):
                skill_id = st.selectbox(
                    "Habilidade",
                    list(skill_names),
                    format_func=skill_names.__getitem__,
                )
                skill_type = st.selectbox(
                    "Tipo de relação",
                    list(SKILL_TYPES),
                    format_func=SKILL_TYPE_LABELS.__getitem__,
                )
                level = st.selectbox(
                    "Nível",
                    list(SKILL_LEVELS),
                    format_func=SKILL_LEVELS.__getitem__,
                )
                years = st.number_input(
                    "Anos de experiência",
                    min_value=0,
                    max_value=80,
                    value=0,
                    step=1,
                )
                modality = st.text_input("Modalidade para ensinar")
                availability = st.text_input("Disponibilidade para ensinar")
                submitted = st.form_submit_button("Adicionar habilidade")
            if submitted:
                user_controller_response = user_controller.add_skill(
                    user_id,
                    skill_id,
                    skill_type,
                    level,
                    int(years) if skill_type != "wants" else None,
                    modality or None,
                    availability or None,
                )
                _handle_profile_response(user_controller_response)

    with st.expander("Adicionar experiência profissional"):
        with st.form("add_experience_form"):
            role = st.text_input("Cargo")
            organization = st.text_input(
                "Empresa ou organização",
                help="Informe o nome de uma organização já cadastrada.",
            )
            start_date = st.date_input("Data de início", value=date.today())
            current_role = st.checkbox("Trabalho aqui atualmente")
            end_date = st.date_input("Data de término", value=date.today())
            description = st.text_area("Descrição da experiência")
            submitted = st.form_submit_button("Adicionar experiência")
        if submitted:
            _handle_profile_response(
                user_controller.add_experience(
                    user_id,
                    {
                        "cargo": role,
                        "organizacao_nome": organization,
                        "data_inicio": start_date,
                        "data_fim": None if current_role else end_date,
                        "descricao": description,
                    },
                )
            )

    with st.expander("Adicionar formação"):
        with st.form("add_education_form"):
            course = st.text_input("Curso")
            institution = st.text_input(
                "Instituição de ensino",
                help="Informe o nome de uma organização já cadastrada.",
            )
            degree = st.selectbox(
                "Grau",
                list(DEGREES),
                format_func=DEGREES.__getitem__,
            )
            has_start_date = st.checkbox("Informar data de início")
            start_date = st.date_input("Início da formação", value=date.today())
            has_end_date = st.checkbox("Informar data de conclusão")
            end_date = st.date_input("Conclusão da formação", value=date.today())
            submitted = st.form_submit_button("Adicionar formação")
        if submitted:
            _handle_profile_response(
                user_controller.add_education(
                    user_id,
                    {
                        "curso": course,
                        "instituicao_nome": institution,
                        "grau": degree,
                        "data_inicio": start_date if has_start_date else None,
                        "data_fim": end_date if has_end_date else None,
                    },
                )
            )

    with st.expander("Adicionar vínculo com organização"):
        organizations = organization_repository.list_all()
        organization_names = {
            str(organization["_id"]): organization["nome"]
            for organization in organizations
        }
        if not organization_names:
            st.info("Ainda não há organizações disponíveis para vincular.")
        else:
            with st.form("add_membership_form"):
                organization_id = st.selectbox(
                    "Organização",
                    list(organization_names),
                    format_func=organization_names.__getitem__,
                )
                role = st.text_input("Papel")
                status = st.text_input("Status", value="ativa")
                has_start_date = st.checkbox("Informar data de início")
                start_date = st.date_input("Início do vínculo", value=date.today())
                submitted = st.form_submit_button("Adicionar vínculo")
            if submitted:
                _handle_profile_response(
                    user_controller.add_membership(
                        user_id,
                        {
                            "organizacao_id": organization_id,
                            "papel": role,
                            "status": status,
                            "desde": start_date if has_start_date else None,
                        },
                    )
                )


def render_profile():
    st.set_page_config(page_title="Perfil profissional", layout="wide")
    st.html(THEME)
    st.title("Perfil profissional")

    from pages.Sessoes import get_authenticated_user_id

    try:
        viewer_id = get_authenticated_user_id()
    except RedisError:
        logger.exception("Falha ao validar a sessão ao abrir um perfil.")
        viewer_id = None
        st.warning(
            "Não foi possível validar sua sessão. O perfil ficará somente para leitura."
        )

    query_user_id = st.query_params.get("user_id") or viewer_id
    if not query_user_id:
        st.info("Informe o parâmetro user_id para visualizar um perfil.")
        return

    try:
        request = UserIdRequest.model_validate({"usuario_id": query_user_id})
    except ValidationError:
        st.error("O identificador do usuário é inválido.")
        return

    user_id = str(request.usuario_id)
    is_owner = viewer_id is not None and str(viewer_id) == user_id

    try:
        user_repository = UserRepository()
        user = user_repository.get_by_id(user_id)
        if user is None:
            st.error("Usuário não encontrado.")
            return

        user.pop("email", None)
        user.pop("senha", None)
        user.pop("nome_normalizado", None)

        user_skill_repository = UserSkillRepository()
        user_organizations_repository = UserOrganizationsRepository()
        skill_repository = SkillRepository()
        organization_repository = OrganizationRepository()
        organization_cache = {}
        organization_relationships = user_organizations_repository.get_by_user_id(
            user_id
        )
        user_controller = None
        if is_owner:
            user_controller = UserController(
                UserService(
                    user_repository,
                    user_skill_repository,
                    user_organizations_repository,
                )
            )

        feedback = st.session_state.pop("profile_feedback", None)
        if feedback and is_owner:
            st.success(feedback)

        _render_profile_identity(user, user_id, viewer_id)

        if user_controller:
            _render_profile_editor(
                user_id,
                user,
                user_controller,
                skill_repository,
                organization_repository,
            )

        if user.get("resumo"):
            st.write(user["resumo"])
        if user.get("aceita_mentoria"):
            st.caption("Disponível para mentoria")

        _render_skills(
            user_id,
            user_skill_repository,
            skill_repository,
            user_controller,
        )
        _render_experiences(
            user,
            organization_repository,
            organization_cache,
            user_id,
            user_controller,
        )
        _render_education(
            user,
            organization_repository,
            organization_cache,
            user_id,
            user_controller,
        )
        _render_certifications(user, organization_repository, organization_cache)
        _render_organization_relationships(
            organization_repository,
            organization_cache,
            organization_relationships,
            user_id,
            user_controller,
        )
        _render_organizations(
            user,
            organization_relationships,
            organization_repository,
            organization_cache,
        )
    except (PyMongoError, Neo4jError, DriverError, RedisError):
        logger.exception(
            "Falha ao carregar o perfil do usuário %s.", user_id
        )
        st.error("Não foi possível carregar o perfil no momento.")


render_profile()
