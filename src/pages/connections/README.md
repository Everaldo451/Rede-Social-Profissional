# Rede de Conexões Profissionais

Contribuição para o estudo de caso 02. O módulo implementa os requisitos RF013 a RF016 e RF019 a RF021.

| Tela | Funcionalidades |
| --- | --- |
| Rede de conexões | Busca por nome e habilidade, envio de solicitação, aceite e recusa, lista de conexões e menor caminho entre profissionais |
| Mentoria | Busca de mentores disponíveis, recomendação por habilidades desejadas e consulta ao perfil do mentor |

## Integração com o aplicativo da equipe

O `src/app.py` registra Rede de Conexões e Mentoria no menu do Streamlit. Após validar a sessão, o login da equipe fornece o identificador MongoDB do usuário.

```python
st.session_state["authenticated_user_id"] = usuario_id_validado
```

No logout ou quando a sessão expirar, o fluxo de autenticação remove essa chave. Para executar pela raiz do projeto, use `uv run streamlit run src/app.py`.

## Contrato de dados

- O MongoDB fornece `usuarios`, `habilidades` e `organizacoes`. A busca e a consulta de perfis usam o formato de documentos do Notion.
- O Neo4j usa `Pessoa.id` como o `_id` do usuário do MongoDB convertido em texto. O módulo grava `SOLICITOU_CONEXAO` e `CONECTADO_COM`. A recomendação usa `DESEJA_DESENVOLVER` e `POSSUI_HABILIDADE`, com `Pessoa.aceita_mentoria` indicando disponibilidade.
- A inicialização do Neo4j da equipe deve garantir que `Pessoa.id` seja único antes de habilitar o envio de solicitações.

## Validação

Com MongoDB e Neo4j de teste configurados, rode `uv run python -m pytest tests/connections -q`. O teste cria perfis temporários para verificar solicitações concorrentes, permissão do destinatário e atualização do menor caminho após o aceite.

[Cartão Rede de Conexões Profissionais no Notion](https://app.notion.com/p/Rede-de-Conex-es-Profissionais-3ff96d7c3b7b8031bdf7ef6041a63235)
