# Rede-Social-Profissional

## Dependências

O projeto usa [uv](https://docs.astral.sh/uv/) para gerenciar dependências. Para
criar o ambiente local e instalar as dependências, incluindo o grupo de
desenvolvimento/testes:

```powershell
uv sync
```

Para iniciar a aplicação em containers, execute:

```powershell
docker compose -f docker/docker-compose.yaml up --build
```

O container inicia o Streamlit automaticamente. Acesse `http://localhost:8501`.

Para executar a aplicação ou os testes localmente, use:

```powershell
uv run streamlit run src/app.py
uv run pytest
```

Adicione dependências da aplicação com `uv add <pacote>` e dependências de
desenvolvimento/testes com `uv add --group dev <pacote>`. Mantenha `uv.lock`
versionado para reproduzir as mesmas versões resolvidas. A imagem Docker instala
somente as dependências da aplicação, sem o grupo `dev`.

Para subir a aplicação com dependências de teste e bancos isolados:

```powershell
docker compose -f docker/docker-compose.test.yaml up -d --build app
```

O container `app` executa o Streamlit e também contém `pytest` e Playwright.
Para acessar o container interativamente:

```powershell
docker compose -f docker/docker-compose.test.yaml exec app sh
```

Já dentro do container, execute:

```sh
uv run pytest
```

Depois dos testes, encerre o ambiente:

```powershell
docker compose -f docker/docker-compose.test.yaml down
```

## Funcionalidades implementadas (publicações)

| Requisito | O que faz | Onde está |
|-----------|-----------|-----------|
| RF009 Criar Publicação | Texto + categoria de TI, tags, trecho de código e mídia (imagem, vídeo, PDF) | `components/post_form.py`, `services/posts/post_service.py` |
| RF010 Editar e Excluir | Só o proprietário edita/exclui (checado no service); exclusão remove comentários e mídia | `components/post_card.py` |
| RF011 Consultar Feed | Mais recentes primeiro, com conteúdo, autor e data; paginação e filtros por categoria/tag | `components/feed.py` |
| RF012 Comentar | Comentários em publicações de outros usuários | `components/comments.py`, `services/posts/comment_service.py` |

Pré-condição "usuário autenticado": cadastro e login (bcrypt) com sessão em Redis.
Dados: usuários, posts e comentários no MongoDB; mídia no GridFS (MongoDB); sessões no Redis.

Dados de exemplo (opcional), com a aplicação no ar:

```powershell
docker compose -f docker/docker-compose.yaml exec app python seed/__init__.py
```

Usuários de exemplo: `ana@exemplo.com`, `bruno@exemplo.com`, `carla@exemplo.com` (senha `senha1234`).

Testes das regras de negócio (não precisam de bancos):

```powershell
uv run pytest tests/services
```


## Arquitetura implementada (DAS v1.4)

A aplicação segue o padrão de monólito modular em camadas:

- `components/` e `pages/`: apresentação Streamlit;
- `controllers/`: entrada das operações, validação dos DTOs e respostas `BaseResponse`;
- `dto/`: contratos e validação de dados com Pydantic;
- `services/`: regras de negócio;
- `repositories/`: persistência e consultas;
- `database/`: clientes MongoDB, Redis e Neo4j.

### Módulos disponíveis

- **Cadastro e perfil profissional:** cadastro/login, atualização do perfil e habilidades;
- **Rede de conexões:** solicitação/aceite de conexões e consultas de conexões mútuas/caminho;
- **Feed e publicações:** RF009, RF010, RF011 e RF012, com mídia, comentários e curtidas;
- **Notificações:** histórico no MongoDB e contador de não lidas no Redis; notificações são geradas para comentários e curtidas;
- **Presença e sessões:** sessões com TTL no Redis e atualização de presença durante o uso da aplicação.

### Persistência por tecnologia

- **MongoDB:** usuários, publicações, comentários, mídias, curtidas, habilidades, habilidades dos usuários, organizações, mentorias e notificações;
- **Redis:** sessões, presença online e contadores de notificações não lidas;
- **Neo4j:** conexões entre usuários, consultas de conexões mútuas e caminhos profissionais.

A aplicação continua sendo um único projeto Python/Streamlit. Os módulos se comunicam por Services e não dependem de uma API REST intermediária.
