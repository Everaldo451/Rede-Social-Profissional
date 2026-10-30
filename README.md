# Rede-Social-Profissional

## Dependências

O projeto usa [uv](https://docs.astral.sh/uv/) para gerenciar dependências. Para
criar o ambiente local e instalar as dependências, incluindo o grupo de
desenvolvimento/testes:

```powershell
uv sync
```

Para executar a aplicação ou os testes dentro do ambiente:

```powershell
uv run streamlit run app.py
uv run pytest
```

Adicione dependências da aplicação com `uv add <pacote>` e dependências de
desenvolvimento/testes com `uv add --group dev <pacote>`. Mantenha `uv.lock`
versionado para reproduzir as mesmas versões resolvidas. A imagem Docker instala
somente as dependências da aplicação, sem o grupo `dev`.
