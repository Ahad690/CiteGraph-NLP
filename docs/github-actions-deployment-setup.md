# GitHub Actions Deployment Setup

This guide documents the deployment pattern used by CiteGraph-NLP so it can be reused for another project.

## Frontend: Firebase Hosting

### 1. Create a Firebase project and Hosting site

1. Create a Firebase project in the Firebase console.
2. Add a Hosting site. The default site usually matches the project id.
3. Install Firebase CLI locally if needed:

```bash
npm install -g firebase-tools
firebase login
```

### 2. Configure Firebase files

Create `.firebaserc` at the repository root:

```json
{
  "projects": {
    "default": "your-firebase-project-id"
  },
  "targets": {
    "your-firebase-project-id": {
      "hosting": {
        "frontend": ["your-hosting-site-id"]
      }
    }
  }
}
```

Create `firebase.json` at the repository root:

```json
{
  "hosting": [
    {
      "target": "frontend",
      "public": "frontend/dist/client",
      "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
      "rewrites": [
        {
          "source": "**",
          "destination": "/index.html"
        }
      ]
    }
  ]
}
```

For a static Firebase deploy, the build output must contain `frontend/dist/client/index.html`.

For TanStack Start apps, generate the HTML shell with built-in SPA prerender settings instead of a custom postbuild script.

Set `frontend/vite.config.ts`:

```ts
import { defineConfig } from "@lovable.dev/vite-tanstack-config";

export default defineConfig({
  tanstackStart: {
    server: { entry: "index" },
    spa: {
      enabled: true,
      maskPath: "/",
      prerender: {
        outputPath: "/index",
      },
    },
  },
});
```

Add `frontend/src/index.ts`:

```ts
export { default } from "./server";
```

Set `frontend/package.json`:

```json
{
  "scripts": {
    "build": "node scripts/build.mjs"
  }
}
```

Use Node 22 in CI for consistent TanStack/Vite prerender behavior.

### 3. Add Firebase GitHub secret

Generate a Firebase service account JSON from:

Firebase Console -> Project settings -> Service accounts -> Generate new private key.

Add it to GitHub:

Repository -> Settings -> Secrets and variables -> Actions -> New repository secret.

Use a name like:

```text
FIREBASE_SERVICE_ACCOUNT_YOUR_PROJECT_ID
```

Paste the full JSON content as the secret value.

### 4. Add the frontend workflow

Create `.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend to Firebase

on:
  push:
    branches:
      - main
    paths:
      - 'frontend/**'
      - 'firebase.json'
      - '.firebaserc'
      - '.github/workflows/deploy-frontend.yml'

jobs:
  build_and_deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '22'

      - name: Install Frontend Dependencies
        working-directory: ./frontend
        run: npm ci || npm install

      - name: Build Frontend
        working-directory: ./frontend
        run: npm run build

      - name: Deploy to Firebase
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: ${{ secrets.GITHUB_TOKEN }}
          firebaseServiceAccount: ${{ secrets.FIREBASE_SERVICE_ACCOUNT_YOUR_PROJECT_ID }}
          channelId: live
          projectId: your-firebase-project-id
```

### 5. Verify

After the workflow succeeds, open:

```text
https://your-hosting-site-id.web.app/
https://your-hosting-site-id.firebaseapp.com/
```

If the deployment succeeds but the URL returns `404`, check that the configured `public` directory contains an `index.html`.

## Backend: Hetzner Docker Deploy

### 1. Prepare the server

Provision a Hetzner server with Ubuntu and SSH access.

On the server, create the project directories:

```bash
mkdir -p /opt/your-app/backend
mkdir -p /opt/your-app/data
```

Install Docker if it is not already installed:

```bash
apt-get update
apt-get install -y docker.io
systemctl enable --now docker
```

Open the backend port in the firewall if needed:

```bash
ufw allow 8002/tcp
ufw allow 22/tcp
```

### 2. Configure SSH access

Create or choose an SSH key that can log in to the server:

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy"
```

Add the public key to the server user's authorized keys:

```bash
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "PASTE_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

Verify from your machine:

```bash
ssh root@your-server-ip "echo SSH_OK"
```

### 3. Add GitHub secret

Add the private key to GitHub Actions secrets:

Repository -> Settings -> Secrets and variables -> Actions -> New repository secret.

Use this name:

```text
HETZNER_SSH_KEY
```

Paste the full private key, including the begin/end lines.

### 4. Add backend Docker files

At minimum, the backend deployment expects:

```text
Dockerfile
.dockerignore
requirements.txt
src/
.env.example
```

Keep real production values in `/opt/your-app/.env` on the server. Do not commit production secrets.

### 5. Add the backend workflow

Create `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend to Hetzner

on:
  workflow_dispatch:
  push:
    branches:
      - main
    paths:
      - 'src/**'
      - 'requirements.txt'
      - 'Dockerfile'
      - '.dockerignore'
      - '.env.example'
      - '.github/workflows/deploy-backend.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      HETZNER_HOST: your-server-ip
      HETZNER_USER: root
      REMOTE_DIR: /opt/your-app/backend
      DATA_DIR: /opt/your-app/data
      ENV_FILE: /opt/your-app/.env
      CONTAINER_NAME: your-app-api
      IMAGE_NAME: your_app_backend
      PORT: 8002
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Configure SSH
        env:
          HETZNER_SSH_KEY: ${{ secrets.HETZNER_SSH_KEY }}
        run: |
          set -euo pipefail
          mkdir -p ~/.ssh
          printf '%s\n' "$HETZNER_SSH_KEY" | tr -d '\r' > ~/.ssh/hetzner_deploy_key
          chmod 600 ~/.ssh/hetzner_deploy_key
          ssh-keyscan -H "$HETZNER_HOST" >> ~/.ssh/known_hosts
          ssh -i ~/.ssh/hetzner_deploy_key -o BatchMode=yes "$HETZNER_USER@$HETZNER_HOST" "echo SSH connection ok"

      - name: Package Backend
        run: |
          set -euo pipefail
          tar -czf /tmp/backend.tar.gz src requirements.txt Dockerfile .dockerignore .env.example

      - name: Upload Backend Bundle
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/hetzner_deploy_key "$HETZNER_USER@$HETZNER_HOST" "mkdir -p '$REMOTE_DIR' '$DATA_DIR'"
          scp -i ~/.ssh/hetzner_deploy_key /tmp/backend.tar.gz "$HETZNER_USER@$HETZNER_HOST:/tmp/backend.tar.gz"

      - name: Deploy Backend
        run: |
          set -euo pipefail
          ssh -i ~/.ssh/hetzner_deploy_key "$HETZNER_USER@$HETZNER_HOST" \
            "REMOTE_DIR='$REMOTE_DIR' DATA_DIR='$DATA_DIR' ENV_FILE='$ENV_FILE' CONTAINER_NAME='$CONTAINER_NAME' IMAGE_NAME='$IMAGE_NAME' PORT='$PORT' bash -s" <<'EOF'
          set -euo pipefail

          mkdir -p "$REMOTE_DIR" "$DATA_DIR"
          tar -xzf /tmp/backend.tar.gz -C "$REMOTE_DIR"
          rm -f /tmp/backend.tar.gz

          if [ ! -f "$ENV_FILE" ]; then
            cp "$REMOTE_DIR/.env.example" "$ENV_FILE"
          fi

          cd "$REMOTE_DIR"
          docker build -t "$IMAGE_NAME" .
          docker stop "$CONTAINER_NAME" 2>/dev/null || true
          docker rm "$CONTAINER_NAME" 2>/dev/null || true
          docker run -d \
            --name "$CONTAINER_NAME" \
            --restart unless-stopped \
            -p "${PORT}:8000" \
            --env-file "$ENV_FILE" \
            -v "${DATA_DIR}:/app/data" \
            "$IMAGE_NAME"
          EOF
```

### 6. Verify

Check the workflow run in GitHub Actions.

Check the server:

```bash
ssh root@your-server-ip "docker ps"
ssh root@your-server-ip "docker logs your-app-api --tail 50"
```

Check the API:

```bash
curl http://your-server-ip:8002/docs
```

## Common Failures

### SSH authentication fails

Error:

```text
ssh: unable to authenticate
```

Check that `HETZNER_SSH_KEY` contains the private key and that the matching public key is in `~/.ssh/authorized_keys` on the server.

### Git clone fails on the server

Error:

```text
could not read Username for 'https://github.com'
```

Avoid cloning from the server unless you configure deploy keys or tokens. The workflow above uploads the checked-out code bundle instead.

### Firebase deploy succeeds but site returns 404

Firebase deployed successfully, but the configured `public` folder does not contain `index.html`. Fix the frontend build or the `firebase.json` `public` path.

### Container starts then restarts

Check logs:

```bash
docker logs your-app-api --tail 100
```

Most runtime failures are missing environment values, missing writable data directories, or Python/Node import errors.
