FROM python:3-alpine AS builder

WORKDIR /noelbundick
COPY src/noelbundick .
RUN python ./setup.py bdist_wheel -d /drop

FROM microsoft/azure-cli:latest

COPY --from=builder /drop /drop
RUN az extension add -y --source /drop/*.whl