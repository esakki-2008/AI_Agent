# AI Agent — Dynamic Client Demo Studio

A premium animated business/agency website with a dynamic public site, Express API and browser-based admin panel. Built as a client demonstration project.

## Features

- Premium animated hero and custom cursor
- Responsive public website
- Interactive project showcase
- Animated project detail modal
- Admin login demo
- Project CRUD: add, edit, publish/draft and delete
- Project image URL manager with preview
- Service visibility controls
- Editable hero content
- Client inquiry collection
- API health indicator
- Persistent JSON data store for demos
- Production single-service Express + Vite setup

## Run locally

```bash
npm install
npm run dev:full
```

Open `http://localhost:5173` for the website.

Open `http://localhost:5173/#admin` for the admin panel.

API health: `http://localhost:4000/api/health`.

## Production build

```bash
npm install
npm run build
npm start
```

The Express server serves the generated Vite `dist` folder and the API from the same service.

## Deployment

`render.yaml` is included for a Render web-service deployment. Set the build command to `npm install && npm run build` and the start command to `npm run start` if configuring manually.

For a separate frontend/backend deployment, set `VITE_API_URL` to the deployed API origin. Locally, Vite proxies `/api` to port 4000.

## Important demo note

The admin login is intentionally a demo/session login and the JSON file is intended for demonstration or small deployments. For a production client, replace this with real authentication, a managed database and protected admin routes.
