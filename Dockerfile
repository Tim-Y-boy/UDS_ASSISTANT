FROM python:3.12-slim

WORKDIR /uds-assistant

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY src/ src/
COPY prompts/ prompts/
COPY config.yaml .

RUN mkdir -p logs/cache logs/callback logs/excel_text logs/llm_raw uploads cache

EXPOSE 8000

CMD ["uvicorn", "src.uds_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]