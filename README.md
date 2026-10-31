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
Rode os testes unitários, de integração e de interface dentro desse mesmo
container:

```powershell
docker compose -f docker/docker-compose.test.yaml exec app uv run pytest
```

Depois dos testes, encerre o ambiente:

```powershell
docker compose -f docker/docker-compose.test.yaml down
```
