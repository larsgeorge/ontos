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

#### API Documentation (Swagger UI)

FastAPI automatically generates interactive API documentation using Swagger UI.
Once the backend server is running (e.g., via `hatch -e dev run dev-backend`), you can access the API documentation in your browser.

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

This interface allows you to explore all available API endpoints, view their request/response models, and even try them out directly from your browser.

# Getting Started

This project uses Yarn for frontend package management, Vite for the frontend build system, and Hatch for the Python backend.

## Available Scripts

In the project directory, you can run:

### `yarn dev:frontend`

Runs the frontend app in development mode using Vite.
Open [http://localhost:3000](http://localhost:3000) (or the port Vite chooses) to view it in the browser.

The page will reload if you make edits.
You will also see any lint errors in the console.

### `yarn dev:backend`

Runs the Python-based FastAPI server in development mode using Hatch.
(Corresponds to the `dev:backend` script in `package.json` which executes `hatch -e dev run dev-backend`)

### `yarn build`

Builds the frontend app for production to the `static` folder.
It performs a TypeScript type check, then correctly bundles React in production mode and optimizes the build for the best performance using Vite.

The build is minified and the filenames include the hashes.
Your app is ready to be deployed!

## Environment Configuration

The application requires a `.env` file in the root directory for configuration. Create a file named `.env` with the following variables (or set them as environment variables):

| Variable                   | Description                                                                                                   | Example Value                                | Required |
|----------------------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------|----------|
| `DATABRICKS_HOST`          | Your Databricks workspace URL                                                                                 | `https://your-workspace.cloud.databricks.com`| Yes      |
| `DATABRICKS_WAREHOUSE_ID`  | The ID of the Databricks SQL Warehouse to use (used by features, not DB)                   | `1234567890abcdef`                           | No    |
| `DATABRICKS_CATALOG`       | Default Unity Catalog catalog (used by features, not DB)                            | `main`                                       | No    |
| `DATABRICKS_SCHEMA`        | Default Unity Catalog schema (used by features, not DB)                             | `default`                                    | No    |
| `DATABRICKS_VOLUME`        | Default Unity Catalog volume for storing app-related files (e.g., data contract outputs)                      | `app_volume`                                 | Yes      |
| `APP_AUDIT_LOG_DIR`        | Directory path within the `DATABRICKS_VOLUME` for storing audit logs                                          | `audit_logs`                                 | Yes      |
| `DATABRICKS_TOKEN`         | Personal access token for Databricks authentication (Optional - SDK can use other methods)                    | `dapi1234567890abcdef`                       | No       |
| `DATABASE_TYPE`            | [Removed] App now uses PostgreSQL for metadata storage.              | `postgres`                                   | -      |
| `POSTGRES_HOST`            | Hostname or IP address of the PostgreSQL server (required if `DATABASE_TYPE` is `postgres`)                   | `localhost` or `your.pg.server.com`          | Cond.    |
| `POSTGRES_PORT`            | Port number for the PostgreSQL server (required if `DATABASE_TYPE` is `postgres`)                             | `5432`                                       | Cond.    |
| `POSTGRES_USER`            | Username for connecting to PostgreSQL (required if `DATABASE_TYPE` is `postgres`)                             | `app_user`                                   | Cond.    |
| `POSTGRES_PASSWORD`        | Password for the PostgreSQL user (required if `DATABASE_TYPE` is `postgres`)                                  | `your_secure_password`                     | Cond.    |
| `POSTGRES_DB`              | Name of the PostgreSQL database to use (required if `DATABASE_TYPE` is `postgres`)                            | `app_ucsak_db`                               | Cond.    |
| `DB_SCHEMA`                | Database schema to use for application tables (Optional, defaults to `public` for PostgreSQL)                 | `myapp_schema`                               | No       |
| `ENV`                      | Deployment environment (`LOCAL`, `DEV`, `PROD`)                                                               | `LOCAL`                                      | No       |
| `DEBUG`                    | Enable debug mode for FastAPI                                                                                 | `True`                                       | No       |
| `LOG_LEVEL`                | Log level for the application (`DEBUG`, `INFO`, `WARNING`, `ERROR`)                                         | `INFO`                                       | No       |
| `LOG_FILE`                 | Path to a log file (if logging to file is desired)                                                            | `/path/to/app.log`                           | No       |
| `APP_ADMIN_DEFAULT_GROUPS` | JSON string array of Databricks group names to assign the default 'Admin' role upon first startup.            | `["admins", "superusers"]`                   | No       |
| `GIT_REPO_URL`             | URL of the Git repository for optional YAML configuration backup/sync                                         | `https://github.com/user/repo.git`         | No       |
| `GIT_BRANCH`               | Git branch to use for configuration backup/sync                                                               | `main`                                       | No       |
| `GIT_USERNAME`             | Username for Git authentication                                                                               | `git_user`                                   | No       |
| `GIT_PASSWORD`             | Password or Personal Access Token for Git authentication                                                      | `git_token_or_password`                      | No       |
| `APP_DEMO_MODE`            | Enable demo mode (loads sample data on startup)                                                               | `False`                                      | No       |
| `APP_DB_DROP_ON_START`     | **DANGER:** Drop and recreate the application database on startup (for development)                           | `False`                                      | No       |
| `APP_DB_ECHO`              | Log SQLAlchemy generated SQL statements to the console (for debugging)                                        | `False`                                      | No       |

**Note:** `DATABRICKS_HTTP_PATH` is derived automatically from `DATABRICKS_WAREHOUSE_ID` for Databricks connections and does not need to be set manually.

### Database Configuration

The application stores its metadata (settings, roles, reviews, etc.) in PostgreSQL only.

Required PostgreSQL variables:

- `POSTGRES_HOST`: Hostname of your PostgreSQL server.
- `POSTGRES_PORT`: Port of your PostgreSQL server (default `5432`).
- `POSTGRES_USER`: Username for PostgreSQL connection.
- `POSTGRES_PASSWORD`: Password for the PostgreSQL user.
- `POSTGRES_DB`: Database name on the PostgreSQL server.
- `POSTGRES_DB_SCHEMA`: Optional schema in the PostgreSQL database (defaults to `public`).

## Prerequisites

- Python 3.10 - 3.12 (as defined in `pyproject.toml`)
- Node.js 16 or higher (which includes npm for installing Yarn)
- Yarn package manager (Version 1.x - Classic). Install via npm if you don't have it:
  ```bash
  npm install --global yarn
  ```
- Hatch (Python build tool)

If you want to use a local PostgreSQL instance for development, here are the steps:

1. Install PostgreSQL locally, here for MacOS:

    ```
    ➜  > brew install postgresql@16
    ==> Downloading https://ghcr.io/v2/homebrew/core/postgresql/16/manifests/16.9
    ############################################################################################################################################ 100.0%
    ==> Fetching postgresql@16
    ==> Downloading https://ghcr.io/v2/homebrew/core/postgresql/16/blobs/sha256:8e883e6e9e7231d49b90965f42ebc53981efb02e6ed7fdcbd1ebfdc2bfb5959a
    ############################################################################################################################################ 100.0%
    ==> Pouring postgresql@16--16.9.arm64_sequoia.bottle.tar.gz
    ==> /opt/homebrew/Cellar/postgresql@16/16.9/bin/initdb --locale=C -E UTF-8 /opt/homebrew/var/postgresql@16
    ==> Caveats
    This formula has created a default database cluster with:
    initdb --locale=C -E UTF-8 /opt/homebrew/var/postgresql@16

    postgresql@16 is keg-only, which means it was not symlinked into /opt/homebrew,
    because this is an alternate version of another formula.

    If you need to have postgresql@16 first in your PATH, run:
    echo 'export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"' >> ~/.zshrc

    For compilers to find postgresql@16 you may need to set:
    export LDFLAGS="-L/opt/homebrew/opt/postgresql@16/lib"
    export CPPFLAGS="-I/opt/homebrew/opt/postgresql@16/include"

    For pkg-config to find postgresql@16 you may need to set:
    export PKG_CONFIG_PATH="/opt/homebrew/opt/postgresql@16/lib/pkgconfig"

    To start postgresql@16 now and restart at login:
    brew services start postgresql@16
    Or, if you don't want/need a background service you can just run:
    LC_ALL="C" /opt/homebrew/opt/postgresql@16/bin/postgres -D /opt/homebrew/var/postgresql@16
    ==> Summary
    🍺  /opt/homebrew/Cellar/postgresql@16/16.9: 3,811 files, 69MB
    ==> Running `brew cleanup postgresql@16`...
    Disable this behaviour by setting HOMEBREW_NO_INSTALL_CLEANUP.
    Hide these hints with HOMEBREW_NO_ENV_HINTS (see `man brew`).
    ```

    Read the emitted instructions above, for example, run `brew services start postgresql@16` if you want to run PostgreSQL in the background.

2. Setup the path and start the CLI as superuser

    ```
    > export PATH="/opt/homebrew/opt/postgresql@16/bin:$PATH"
    > psql -U $(whoami) -d postgres
    psql (16.9 (Homebrew))
    Type "help" for help.
    ```

3. Run the necessary commands to create resources

    ```sql
    postgres=# CREATE ROLE rucsak_app_user WITH LOGIN PASSWORD '<my_password>';
    postgres=# CREATE DATABASE app_ucsak;
    postgres=# GRANT ALL PRIVILEGES ON DATABASE app_ucsak TO rucsak_app_user;
    postgres=# GRANT USAGE ON SCHEMA public TO rucsak_app_user;
    postgres=# GRANT CREATE ON SCHEMA public TO rucsak_app_user;

    postgres=# 
    \q
    ```

    Note: Replace `<my_password>` with your password of choice.

4. Log in as the app user role and create remaining resources

    ```sql
    ➜  ucapp git:(main) ✗ psql -U rucsak_app_user -d app_ucsak
    psql (16.9 (Homebrew))
    Type "help" for help.
    app_ucsak=> CREATE SCHEMA app_ucsak;
    app_ucsak=> GRANT USAGE ON SCHEMA app_ucsak TO rucsak_app_user;
    app_ucsak=> GRANT ALL ON SCHEMA app_ucsak TO rucsak_app_user;
    ```

5. Configure app to use local database 

    ```env
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432
    POSTGRES_USER=rucsak_app_user
    POSTGRES_PASSWORD=<my_password>
    POSTGRES_DB=app_ucsak
    POSTGRES_DB_SCHEMA=app_ucsak
    ```

    Note: Use the above `<my_password>` here
    
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

# Development

To run both frontend and backend servers in development mode:

**1. Start the Frontend Development Server:**

Open a terminal and run:
```bash
yarn install && yarn dev:frontend
```
This will install frontend dependencies (if needed) and start the Vite development server, typically on port 3000.

**2. Start the Backend Development Server:**

Open a separate terminal and run:
```bash
yarn dev:backend
```
This command uses Yarn to execute the `dev:backend` script from `package.json`, which in turn uses Hatch to run the FastAPI backend in the development environment (`-e dev`), usually starting it on port 8000.

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

## Default Application Roles

On first startup, if no roles exist in the database, the application creates a set of default roles with predefined permissions:

- **Admin:** Full administrative access to all features. Assigned to groups specified by the `APP_ADMIN_DEFAULT_GROUPS` environment variable.
- **Data Governance Officer:** Broad administrative access, typically excluding low-level system settings.
- **Data Steward:** Read/Write access to specific data governance features (Data Products, Contracts, Glossary).
- **Data Consumer:** Read-only access to data discovery features.
- **Data Producer:** Read-only access generally, with write access to create/manage Data Products and Contracts.
- **Security Officer:** Administrative access to security and entitlements features.

These roles and their permissions can be viewed and modified in the application's Settings -> RBAC section after initial startup.

## Environment Variables

For a comprehensive list and explanation of required and optional environment variables, please refer to the **[Environment Configuration](#environment-configuration)** section earlier in this document.

A complete template can also be found in the `.env.example` file in the project root.

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

# License

This project is licensed under the Apache License, Version 2.0 - see the LICENSE file for details.
