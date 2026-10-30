FROM python:latest

WORKDIR /app

ENV PYTHONPATH=/app
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir uv==0.13.6

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
