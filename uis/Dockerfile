FROM node:22-alpine

WORKDIR /workspace/uis
COPY . .

RUN npm install --prefix /workspace/uis/talent-pipeline-tracker \
    && npm install --prefix /workspace/uis/backoffice \
    && chmod +x /workspace/uis/start.sh

EXPOSE 3000
CMD ["./start.sh"]