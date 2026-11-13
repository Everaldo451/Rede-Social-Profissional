# Centraliza os valores aceitos nos formulários e seus rótulos de exibição.
"""Listas de opções fixas (chave gravada no banco -> rótulo exibido)."""

# As chaves identificam o vínculo do usuário com uma habilidade.
SKILL_TYPES = {
    "has": "Possui",
    "wants": "Quer desenvolver",
    "teaches": "Ensina",
}

# Níveis disponíveis para declarar uma competência.
SKILL_LEVELS = {
    "iniciante": "Iniciante",
    "intermediario": "Intermediário",
    "avancado": "Avançado",
    "especialista": "Especialista",
}

# Graus de formação utilizados no cadastro acadêmico.
DEGREES = {
    "tecnico": "Técnico",
    "tecnologo": "Tecnólogo",
    "graduacao": "Graduação",
    "bacharelado": "Bacharelado",
    "especializacao": "Especialização / MBA",
    "mestrado": "Mestrado",
    "doutorado": "Doutorado",
    "curso_livre": "Curso livre",
}

# Tipos aceitos no cadastro de organizações.
ORGANIZATION_TYPES = {
    "empresa": "Empresa",
    "startup": "Startup",
    "instituicao_ensino": "Instituição de ensino",
    "ong": "ONG / sem fins lucrativos",
    "orgao_publico": "Órgão público",
    "outro": "Outro",
}
