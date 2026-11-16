# Development containers

Docker Engine and Compose are required. The root Compose file starts one UI
container and one FastAPI container:

- Port 3000: the website, currently an under-construction placeholder.
- Port 3001: the existing Next.js tracker, which provides login and proxies the
  static backoffice at `/backoffice/`.
- Port 8012: the FastAPI service.

The backoffice is not a standalone Next.js app. Its esbuild watcher rebuilds
assets as source files change; refresh the browser to see those changes.
Next.js and Uvicorn use their development reloaders. Next.js proxies backend
requests over the Docker network using `backend:8012`; browsers use the
port-3001 origin and must not use that internal Docker hostname directly.

## Configuration and startup

Create the ignored root `.env` before starting. The API requires a unique,
random `JWT_SECRET_KEY` of at least 32 bytes; obtain a separate secret through
your team's secure process. Do not commit credentials. Inventory also needs
`SUPABASE_DATABASE_URL` or all of `SUPABASE_DB_HOST`, `SUPABASE_DB_PORT`,
`SUPABASE_DB_NAME` (or `SUPABASE_DB_DATABASE`), `SUPABASE_DB_USER`, and
`SUPABASE_DB_PASSWORD`. Without a database configuration inventory returns
503; an unreachable configured database prevents API startup.

`AUTH_API_URL` and `NEXT_PUBLIC_INVENTORY_API_URL` default to
`http://backend:8012` inside Compose and may be overridden in `.env`.
`FRONTEND_BASE_URL` defaults to `http://localhost:3001` for local password-reset
links; set it to the externally reachable backoffice URL in other environments.
These URLs have different audiences: the first two are server-side proxy
destinations, while password-reset links are opened by a user.

From the repository root:

```sh
docker compose up --build
```

Open `http://localhost:3000/` for the website and
`http://localhost:3001/backoffice/` for the backoffice. Register or log in via
`http://localhost:3001/login`. `docker compose ps` shows the container status.
The API's `/health` endpoint requires authentication.

The `data` directory is bind-mounted and contains persistent application data.
Do not delete it when stopping containers. Node dependencies and Next.js caches
use named volumes so host dependencies do not overwrite container dependencies.
After changing a UI lockfile, rebuild the image and refresh the corresponding
dependency volume, for example:

```sh
docker compose build ui
docker compose up -d ui
docker compose exec ui npm ci --prefix /workspace/uis/website
```

Use the corresponding `backoffice` or `talent-pipeline-tracker` path for those
apps. Restart the UI container after refreshing dependencies.

## VPS deployment

No VPS deployment is included or verified. Provision the configuration on the
server without committing it, back up persistent data, and arrange a trusted
TLS reverse proxy, firewall, and externally reachable `FRONTEND_BASE_URL`.
This Compose configuration runs development servers with reload enabled and
publishes all three ports; it is not a hardened public production deployment.
Do not expose it directly to the internet as production. Validate the server
configuration, both UI routes, authenticated API requests, database access,
and container status on the VPS before claiming deployment.
