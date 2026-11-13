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

## Carregar dados de exemplo

Com os containers da aplicação em execução, entre no container `app`:

```powershell
docker compose -f docker/docker-compose.yaml exec app sh
```

Dentro do container, execute o arquivo de seed a partir da raiz do projeto:

```sh
python seed/__init__.py
```

As contas de demonstração usam a senha `RedeSocial@2026`; o seed converte as
senhas para hashes bcrypt antes de gravá-las.

O comando atualiza ou insere os documentos dos arquivos em `seed/collections`,
cria os índices definidos e recalcula `notifications:unread:<user_id>` com base
nas notificações não lidas do MongoDB. No Neo4j, cria ou atualiza nós e
relacionamentos derivados de habilidades, experiências, formação e mentorias.
Os relacionamentos `CONECTADO_COM`, `SOLICITOU_CONEXAO`, `MEMBRO_DE` e `ENSINA`
são carregados dos arquivos JSON em `seed/rellationships`; `ENSINA` é mantido
independente de `aceita_mentoria` e das habilidades declaradas nos usuários.
O seed não apaga documentos MongoDB, chaves Redis, nem nós ou relacionamentos
existentes fora dos dados de seed. Os dois documentos de `midias.files.json`
servem como modelos de metadados: o seed cria arquivos de perfil/publicação para
cada usuário e post, usando os SVGs locais em `seed/assets`, e os grava pelo
GridFS para criar tanto `midias.files` quanto `midias.chunks`.
