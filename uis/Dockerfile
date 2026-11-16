FROM node:22-alpine

WORKDIR /workspace/uis
COPY . .

RUN npm ci --prefix /workspace/uis/website \
    && npm ci --prefix /workspace/uis/talent-pipeline-tracker \
    && npm ci --prefix /workspace/uis/backoffice \
    && chmod +x /workspace/uis/start.sh

EXPOSE 3000 3001
CMD ["sh", "./start.sh"]