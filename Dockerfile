FROM node:24-bookworm-slim AS web
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi; npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/tandem.db FRONTEND_DIST=/opt/tandem/web PORT=8000
WORKDIR /opt/tandem/backend
COPY backend/requirements.txt ./
RUN --mount=type=secret,id=build_ca \
    if [ -f /run/secrets/build_ca ]; then export PIP_CERT=/run/secrets/build_ca; fi; \
    pip install --no-cache-dir -r requirements.txt \
    && useradd --system --create-home --uid 10001 tandem \
    && install -d -o tandem -g tandem /data
COPY --chown=tandem:tandem backend/app ./app
COPY --chown=tandem:tandem backend/alembic.ini ./
COPY --chown=tandem:tandem backend/alembic ./alembic
COPY --from=web --chown=tandem:tandem /build/dist /opt/tandem/web
USER tandem
VOLUME ["/data"]
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port \"$PORT\""]
