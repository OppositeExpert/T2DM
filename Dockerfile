FROM python:3.12.0-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLCONFIGDIR=/workspace/outputs/.matplotlib

WORKDIR /workspace
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.lock pyproject.toml ./
COPY src ./src
RUN python -m pip install --no-cache-dir -r requirements.lock \
    && python -m pip install --no-cache-dir --no-deps --no-build-isolation -e .
COPY config ./config
COPY scripts ./scripts
COPY tests ./tests
COPY docs ./docs
COPY evidence ./evidence
COPY results/final_publication ./results/final_publication
COPY README.md FINAL_RUN_CHECKLIST.md PUBLICATION_READINESS.md CONTRIBUTING.md LICENSE_STATUS.md CITATION.cff ./

CMD ["python", "-m", "diabetes_pipeline.cli", "--help"]
