# Regras de contas e perfis: autenticação, privacidade, habilidades e histórico profissional.
import logging

from common.choices import SKILL_LEVELS, SKILL_TYPES
from common.errors import ConflictError, ForbiddenError, InvalidDataError, NotFoundError, UnauthorizedError
from common.security import hash_password
from common.validation import normalize_key, require_choice

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 100
REPOSITORY_FILTER_FIELDS = {
    "usuario_id": "_id",
}


def present_user(user, *, include_private=False) -> dict:
    """Dados do usuário que podem sair do backend.

    O e-mail é um dado privado: só aparece para o próprio usuário.
    """
    data = {
        "usuario_id": user.get("_id"),
        "nome": user.get("nome"),
        "headline": user.get("headline"),
        "resumo": user.get("resumo"),
        "localizacao": user.get("localizacao"),
        "criado_em": user.get("criado_em"),
    }
    for field in (
        "habilidades",
        "experiencias",
        "formacao",
        "certificacoes",
        "relacionamentos_habilidades",
        "relacionamentos_organizacoes",
    ):
        if field in user:
            data[field] = user[field]
    if include_private:
        data["email"] = user.get("email")
    return data


class UserService:
    def __init__(
        self,
        user_repository,
        user_skill_repository,
        user_organization_repository,
        notification_service=None,
    ):
        self.user_repository = user_repository
        self.user_skill_repository = user_skill_repository
        self.user_organization_repository = user_organization_repository
        self.notification_service = notification_service

    # ---- cadastro ---------------------------------------------------------
    # Impede e-mail duplicado, gera o hash da senha e cadastra o perfil inicial.
    def create(self, data):
        name = data["nome"]
        email = data["email"]
        password = data["senha"]

        if self.user_repository.get_by_email(email):
            raise ConflictError("Este e-mail já está cadastrado.")

        user = self.user_repository.create(
            {
                "nome": name,
                "nome_normalizado": normalize_key(name),
                "email": email,
                "senha": hash_password(password),
                "headline": "",
                "resumo": "",
                "localizacao": "",
            }
        )
        self._send_welcome(user["_id"])
        return present_user(user, include_private=True)

    # Tenta enviar uma mensagem de boas-vindas, registrando falhas sem interromper o cadastro.
    def _send_welcome(self, usuario_id) -> None:
        if not self.notification_service:
            return
        try:
            self.notification_service.notify("welcome", usuario_id)
        except Exception:  # a notificação nunca pode quebrar o cadastro
            logger.warning("Não foi possível criar a notificação de boas-vindas.", exc_info=True)

    # ---- autenticação -----------------------------------------------------
    # Normaliza o e-mail, verifica as credenciais e retorna os dados do próprio usuário.
    def authenticate(self, email, senha):
        if not isinstance(email, str) or not isinstance(senha, str) or not email.strip() or not senha:
            raise UnauthorizedError("E-mail ou senha inválidos.")
        user = self.user_repository.authenticate(email.strip().lower(), senha)
        if user is None:
            raise UnauthorizedError("E-mail ou senha inválidos.")
        return present_user(user, include_private=True)

    # ---- consulta ---------------------------------------------------------
    def get_by_id(self, usuario_id, visualizador_id=None):
        """Perfil de um usuário, respeitando as permissões de acesso.

        - Sem usuário logado (visualizador_id vazio): acesso negado.
        - O próprio usuário vê tudo, inclusive o e-mail.
        - Outros usuários logados veem apenas os dados públicos.
        """
        if not visualizador_id:
            raise ForbiddenError("Faça login para ver perfis.")
        user = self.user_repository.get_by_id(usuario_id)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        user["relacionamentos_habilidades"] = self.user_skill_repository.get_skills(
            {"usuario_id": usuario_id}
        )
        user["relacionamentos_organizacoes"] = (
            self.user_organization_repository.get_by_user_id(usuario_id)
        )
        return present_user(user, include_private=(visualizador_id == usuario_id))

    # Retorna os usuários apenas com os dados permitidos na apresentação pública.
    def list_all(self):
        return [present_user(user) for user in self.user_repository.list_all()]

    # Ajusta a paginação, traduz filtros para o repositório e apresenta os dados públicos.
    def get_paginated(self, offset, limit, filters=None):
        offset = max(int(offset or 0), 0)
        limit = min(max(int(limit or 20), 1), MAX_PAGE_SIZE)
        repository_filters = {}
        for key, value in (filters or {}).items():
            root, separator, suffix = key.partition(".")
            mapped_key = REPOSITORY_FILTER_FIELDS.get(root, root)
            repository_filters[
                f"{mapped_key}{separator}{suffix}" if separator else mapped_key
            ] = value
        users = self.user_repository.get_paginated(offset, limit, repository_filters)
        return [present_user(user) for user in users]

    # ---- edição -----------------------------------------------------------
    # Seleciona os campos editáveis e atualiza o perfil com seu nome normalizado.
    def update(self, usuario_id, data):
        changes = {}
        if "nome" in data:
            changes["nome"] = data["nome"]
            changes["nome_normalizado"] = normalize_key(changes["nome"])
        if "headline" in data:
            changes["headline"] = data["headline"]
        if "resumo" in data:
            changes["resumo"] = data["resumo"]
        if "localizacao" in data:
            changes["localizacao"] = data["localizacao"]
        if not changes:
            raise InvalidDataError("Nenhuma informação para atualizar.")

        user = self.user_repository.update(usuario_id, changes)
        if user is None:
            raise NotFoundError("Usuário não encontrado.")
        return present_user(user, include_private=True)

    # Valida tipo, nível e detalhes exigidos antes de vincular a habilidade ao usuário.
    def add_skill(
        self,
        usuario_id,
        habilidade_id,
        tipo,
        nivel=None,
        experiencia_anos=None,
        modalidade=None,
        disponibilidade=None,
    ):
        require_choice(tipo, SKILL_TYPES, "tipo de competência")
        if nivel is None:
            raise InvalidDataError("O nível de competência é obrigatório.")
        require_choice(nivel, SKILL_LEVELS, "nível de competência")
        if experiencia_anos is not None and (
            isinstance(experiencia_anos, bool)
            or not isinstance(experiencia_anos, int)
            or experiencia_anos < 0
        ):
            raise InvalidDataError("Os anos de experiência são inválidos.")
        if tipo == "has" and experiencia_anos is None:
            raise InvalidDataError(
                "Informe os anos de experiência para a habilidade."
            )
        if tipo == "teaches" and (
            experiencia_anos is None or not modalidade or not disponibilidade
        ):
            raise InvalidDataError(
                "Informe experiência, modalidade e disponibilidade para ensinar."
            )

        added = self.user_skill_repository.add_skill(
            usuario_id,
            habilidade_id,
            tipo,
            nivel=nivel,
            experiencia_anos=experiencia_anos,
            modalidade=modalidade,
            disponibilidade=disponibilidade,
        )
        if not added:
            raise NotFoundError("Usuário ou habilidade não encontrados.")
        return {
            "usuario_id": usuario_id,
            "habilidade_id": habilidade_id,
            "tipo": tipo,
            "nivel": nivel,
            "experiencia_anos": experiencia_anos,
            "modalidade": modalidade,
            "disponibilidade": disponibilidade,
        }

    # Valida o tipo de vínculo e exige que a relação removida exista.
    def remove_skill(self, usuario_id, habilidade_id, tipo):
        require_choice(tipo, SKILL_TYPES, "tipo de competência")
        if not self.user_skill_repository.remove_skill(usuario_id, habilidade_id, tipo):
            raise NotFoundError("Relacionamento de habilidade não encontrado.")
        return True

    # Consulta as habilidades e os vínculos que atendem aos filtros recebidos.
    def get_skills(self, filters=None):
        return self.user_skill_repository.get_skills(filters)

    # Monta os dados da experiência profissional para o repositório de organizações.
    def add_experience(self, usuario_id, data):
        experience = {
            "organizacao_id": data.get("organizacao_id"),
            "organizacao_nome": data.get("organizacao_nome"),
            "cargo": data["cargo"],
            "data_inicio": data["data_inicio"],
            "data_fim": data.get("data_fim"),
            "atual": data.get("data_fim") is None,
            "descricao": data.get("descricao") or "",
        }
        return self.user_organization_repository.add_experience(usuario_id, experience)

    # Remove a experiência identificada e sinaliza quando o vínculo não existe.
    def remove_experience(
        self, usuario_id, organizacao_id, cargo, data_inicio
    ):
        if not self.user_organization_repository.remove_experience(
            usuario_id, organizacao_id, cargo, data_inicio
        ):
            raise NotFoundError("Experiência não encontrada.")
        return True

    # Monta os dados da formação acadêmica para persistência.
    def add_education(self, usuario_id, data):
        education = {
            "instituicao_id": data.get("instituicao_id"),
            "instituicao_nome": data.get("instituicao_nome"),
            "curso": data["curso"],
            "grau": data["grau"],
            "data_inicio": data.get("data_inicio"),
            "data_fim": data.get("data_fim"),
        }
        return self.user_organization_repository.add_education(usuario_id, education)

    # Remove a formação identificada por instituição, curso e grau.
    def remove_education(
        self, usuario_id, instituicao_id, curso, grau
    ):
        if not self.user_organization_repository.remove_education(
            usuario_id, instituicao_id, curso, grau
        ):
            raise NotFoundError("Formação não encontrada.")
        return True

    # Encaminha a inclusão do vínculo com a organização e verifica seu resultado.
    def add_membership(self, usuario_id, data):
        added = self.user_organization_repository.add_membership(
            usuario_id,
            data["organizacao_id"],
            data["papel"],
            data["status"],
            data.get("desde"),
        )
        if not added:
            raise NotFoundError("Não foi possível adicionar o vínculo.")
        return True

    # Remove o vínculo com a organização identificado pelo papel do usuário.
    def remove_membership(self, usuario_id, organizacao_id, papel):
        if not self.user_organization_repository.remove_membership(
            usuario_id, organizacao_id, papel
        ):
            raise NotFoundError("Vínculo com a organização não encontrado.")
        return True

    # Verifica a existência da conta e remove seus relacionamentos antes do documento do usuário.
    def delete(self, usuario_id):
        if self.user_repository.get_by_id(usuario_id) is None:
            raise NotFoundError("Usuário não encontrado.")
        self.user_organization_repository.delete_by_user_id(usuario_id)
        if not self.user_repository.delete(usuario_id):
            raise NotFoundError("Usuário não encontrado.")
        return True
