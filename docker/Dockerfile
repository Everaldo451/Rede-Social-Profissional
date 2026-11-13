# Imagem da aplicação com Python, uv e as dependências de execução.
FROM python:latest

# Define a pasta de trabalho usada pelos comandos seguintes.
WORKDIR /app

# Torna os módulos de src e os executáveis do ambiente virtual acessíveis no container.
ENV PYTHONPATH=/app/src
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.6

# Copia primeiro os arquivos de dependências para aproveitar o cache da construção.
COPY pyproject.toml uv.lock ./
# Instala as versões do lockfile sem incluir o grupo de ferramentas de desenvolvimento.
RUN uv sync --locked --no-dev --no-install-project

# Inclui os arquivos do projeto após a instalação das dependências.
COPY . .

EXPOSE 8501

# Inicia o Streamlit aceitando conexões pelas interfaces de rede do container.
CMD ["streamlit", "run", "src/app.py", "--server.address=0.0.0.0"]
