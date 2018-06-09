FROM microsoft/azure-cli:latest

COPY / /drop
RUN az extension add -y --source /drop/*.whl