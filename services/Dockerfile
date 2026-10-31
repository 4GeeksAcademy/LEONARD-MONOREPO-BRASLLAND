FROM python:3.12-slim

WORKDIR /workspace
COPY . /workspace/services
COPY --from=packages . /workspace/packages
COPY --from=shared . /workspace/shared

RUN pip install --no-cache-dir uv \
    && uv pip install --system -r /workspace/services/api/requirements.txt

EXPOSE 8012
CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8012", "--reload"]