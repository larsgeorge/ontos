# Unity Catalog Swiss Army Knife

A comprehensive tool for managing Databricks Unity Catalog resources, featuring a React frontend with Tailwind CSS and Shadcn UI, powered by a FastAPI backend.

![Home](docs/images/home.png)

## Overview

The Unity Catalog Swiss Army Knife provides a unified interface for managing various aspects of Databricks Unity Catalog, including:

- Data Products management
- Data Contracts handling
- Business Glossaries
- Master Data Management
- Advanced Catalog operations

## Architecture

### Frontend (React + TypeScript)

The frontend is built with React, TypeScript, Tailwind CSS, and Shadcn UI, providing a modern and responsive user interface.

Key features:
- Tab-based navigation
- Real-time data synchronization
- Interactive data management interfaces
- Responsive dashboard with summary metrics
- Clean, accessible UI components with Shadcn UI

### Backend (Python + FastAPI)

The backend API is built with FastAPI, providing RESTful endpoints for all data operations.

#### API Endpoints

##### Data Products

# Getting Started

This project uses Vite for the frontend build system and Hatch for the Python backend.

## Available Scripts

In the project directory, you can run:

### `npm run dev`

Runs the app in development mode with Vite.\
Open [http://localhost:3000](http://localhost:3000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

### `npm run dev:backend`

Runs the Python-based FastAPI server in development mode.

### `npm run test`

Launches the test runner in the interactive watch mode.

### `npm run build`

Builds the app for production to the `static` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

## Environment Configuration

The application requires a `.env` file in the root directory for configuration. Create a file named `.env` with the following variables:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| DATABRICKS_HOST | Your Databricks workspace URL | https://your-workspace.cloud.databricks.com |
| DATABRICKS_TOKEN | Personal access token for authentication | dapi1234567890abcdef |
| DATABRICKS_HTTP_PATH | SQL warehouse HTTP path | /sql/1.0/warehouses/abc123 |
| DATABRICKS_CATALOG | Default catalog to use | main |
| DATABRICKS_SCHEMA | Default schema to use | default |

# Unified Catalog Application

A modern web application for managing data catalogs, built with FastAPI and React with Tailwind CSS and Shadcn UI.

## Prerequisites

- Python 3.10 - 3.12 (as defined in `pyproject.toml`)
- Node.js 16 or higher
- Yarn package manager
- Hatch (Python build tool)

## Installation

1. Install Hatch (if you haven't already):
```bash
pip install hatch
```

2. Install Frontend Dependencies:
Navigate to the project root directory and run:
```bash
yarn install
```

3. Backend Dependencies:
Python dependencies for the backend are managed by Hatch. They will be installed automatically when you run backend commands within the Hatch environment (e.g., `hatch run ...` or `hatch shell`).

**Note on Dependencies:** Since this application is designed to run as a Databricks App, which utilizes a standard Python environment, the backend dependencies are listed in `requirements.txt`. The `pyproject.toml` file is configured (using the `hatch-requirements-txt` plugin) to dynamically read its dependencies from `requirements.txt`. This ensures that the dependencies used in local development with Hatch are consistent with those installed in the Databricks App environment.

## Development

To run both frontend and backend servers in development mode:

**1. Start the Frontend Development Server:**

Open a terminal and run:
```bash
yarn install && yarn dev
```
This will install frontend dependencies (if needed) and start the Vite development server, typically on port 3000.

**2. Start the Backend Development Server:**

Open a separate terminal and run:
```bash
hatch -e dev run dev-backend
```
This command uses Hatch to run the FastAPI backend in the development environment (`-e dev`), usually starting it on port 8000.

Both servers support hot reloading for a smoother development experience.

## Building for Production

**1. Build the Frontend:**

```bash
yarn build
```
This command builds the React application using Vite. The output files will be placed in the `./static/` directory at the project root. It also performs a TypeScript type check (`tsc --noEmit`).

**2. Build the Backend:**

```bash
hatch build
```
This command uses Hatch to build the Python backend package (typically a wheel file) according to the configuration in `pyproject.toml`.

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
DATABRICKS_WAREHOUSE_ID=your_warehouse_id
DATABRICKS_HTTP_PATH=your_http_path
DATABRICKS_CATALOG=your_catalog
DATABRICKS_SCHEMA=your_schema
```

## Project Structure

```
ucapp/
├── api/                    # Backend FastAPI application
│   ├── common/
│   ├── controller/
│   ├── data/
│   ├── db_models/
│   ├── models/
│   ├── repositories/
│   ├── routes/
│   ├── schemas/
│   ├── utils/
│   ├── workflows/
│   ├── app.py            # Main application file
│   └── app.yaml          # Databricks App config
├── src/                    # Frontend React application
│   ├── components/
│   ├── config/
│   ├── hooks/
│   ├── lib/
│   ├── stores/
│   ├── types/
│   ├── views/
│   ├── App.tsx           # Main app component
│   └── main.tsx          # Application entry point
├── static/                 # Static files (frontend build output)
├── public/                 # Public assets (served by Vite dev server)
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS configuration
├── components.json         # Shadcn UI configuration
├── tsconfig.json           # TypeScript config for src
├── tsconfig.node.json      # TypeScript config for build/dev tooling
├── pyproject.toml          # Hatch configuration & backend dependencies
├── package.json            # Frontend dependencies & scripts (yarn)
├── yarn.lock               # Yarn lock file
├── README.md               # This file
├── LICENSE                 # Apache 2.0 License
└── .env.example            # Example environment variables
```

## Contributing

1. Create a new branch for your feature
2. Make your changes
3. Run tests and linting:
```bash
hatch run test:cov
hatch run lint:all
```
4. Submit a pull request

## License

This project is licensed under the Apache License, Version 2.0 - see the LICENSE file for details.
