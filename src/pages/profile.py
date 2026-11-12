import logging
from datetime import date, datetime

import streamlit as st
from pydantic import ValidationError

from dto.profile.request.user_requests import UserIdRequest
from repositories.profile.organization_repository import OrganizationRepository
from repositories.profile.skill_repository import SkillRepository
from repositories.profile.user_organizations_repository import (
    UserOrganizationsRepository,
)
from repositories.profile.user_repository import UserRepository
from repositories.profile.user_skill_repository import UserSkillRepository

logger = logging.getLogger(__name__)

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


def _render_experiences(user, organization_repository, organization_cache):
    st.subheader("Experiência profissional")
    experiences = user.get("experiencias") or []
    if not experiences:
        st.caption("Nenhuma experiência informada.")
        return

    for experience in experiences:
        organization_name = _organization_name(
            organization_repository,
            experience.get("organizacao_id"),
            organization_cache,
        )
        st.markdown(f"**{experience.get('cargo', 'Cargo não informado')} — {organization_name}**")
        start = _format_date(experience.get("data_inicio"))
        end = (
            "Atual"
            if experience.get("atual")
            else _format_date(experience.get("data_fim"))
        )
        st.write(f"{start} – {end}")
        if experience.get("descricao"):
            st.write(experience["descricao"])


def _render_education(user, organization_repository, organization_cache):
    st.subheader("Formação")
    education_entries = user.get("formacao") or []
    if not education_entries:
        st.caption("Nenhuma formação informada.")
        return

    for education in education_entries:
        institution_name = _organization_name(
            organization_repository,
            education.get("instituicao_id"),
            organization_cache,
        )
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


def _render_skills(
    user_id,
    user_skill_repository,
    skill_repository,
):
    st.subheader("Habilidades")
    relationships = user_skill_repository.get_skills({"usuario_id": user_id})
    if not relationships:
        st.caption("Nenhuma habilidade informada.")
        return

    for relationship in relationships:
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
        st.markdown(f"**{skill_name}**")
        st.write(" · ".join(details))


def _render_organization_relationships(
    organization_repository,
    organization_cache,
    relationships,
):
    st.subheader("Relacionamentos com organizações")
    if not relationships:
        st.caption("Nenhum relacionamento com organização informado.")
        return

    for relationship in relationships:
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


def render_profile():
    st.set_page_config(page_title="Perfil profissional", layout="wide")
    st.title("Perfil profissional")

    query_user_id = st.query_params.get("user_id")
    if not query_user_id:
        st.info("Informe o parâmetro user_id para visualizar um perfil.")
        return

    try:
        request = UserIdRequest.model_validate({"usuario_id": query_user_id})
    except ValidationError:
        st.error("O identificador do usuário é inválido.")
        return

    try:
        user = UserRepository().get_by_id(request.usuario_id)
        if user is None:
            st.error("Usuário não encontrado.")
            return

        organization_repository = OrganizationRepository()
        organization_cache = {}
        organization_relationships = UserOrganizationsRepository().get_by_user_id(
            request.usuario_id
        )
        st.header(user.get("nome", "Perfil sem nome"))

        profile_details = [
            user.get("headline"),
            user.get("localizacao"),
            user.get("nivel_carreira"),
        ]
        st.write(" · ".join(value for value in profile_details if value) or " ")
        if user.get("resumo"):
            st.write(user["resumo"])
        if user.get("aceita_mentoria"):
            st.caption("Disponível para mentoria")

        _render_skills(
            request.usuario_id,
            UserSkillRepository(),
            SkillRepository(),
        )
        _render_experiences(user, organization_repository, organization_cache)
        _render_education(user, organization_repository, organization_cache)
        _render_certifications(user, organization_repository, organization_cache)
        _render_organization_relationships(
            organization_repository,
            organization_cache,
            organization_relationships,
        )
        _render_organizations(
            user,
            organization_relationships,
            organization_repository,
            organization_cache,
        )
    except Exception:
        logger.exception(
            "Falha ao carregar o perfil do usuário %s.", request.usuario_id
        )
        st.error("Não foi possível carregar o perfil no momento.")


render_profile()
