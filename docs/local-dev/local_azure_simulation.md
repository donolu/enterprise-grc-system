# Local Development Environment Guide

## 1. Introduction
This guide provides instructions for setting up and running the local development environment. Our setup uses Docker Compose to simulate the production Azure cloud environment, ensuring consistency and reducing "it works on my machine" issues.

## 2. Core Tool: Docker Compose
The entire local stack is defined and orchestrated by the `compose.yml` file in the project root. This file configures all the services needed to run the full application on your local machine.

## 3. Service Breakdown
The `compose.yml` file includes the following services:

*   `web`: The main Django application running on Gunicorn. This is the backend API.
*   `frontend`: The Next.js development server that provides the user interface with hot-reloading.
*   `worker` & `beat`: The Celery services that execute background and scheduled tasks (e.g., sending emails).
*   `postgres`: A PostgreSQL database container, serving as a direct stand-in for the production Azure PostgreSQL service.
*   `redis`: A Redis container, acting as the message broker for Celery and a caching layer, just like Azure Cache for Redis in production.
*   `azurite`: A local storage emulator from Microsoft that mimics Azure Blob Storage. All file uploads during local development will go here.
*   `mailhog`: A local email-catching server. It intercepts all outgoing emails from the application, allowing you to view them in a web interface without sending real emails to users.
*   `onlyoffice`: The full ONLYOFFICE Document Server, enabling inline editing of documents.
*   `opensearch`: A local search engine that stands in for the production Azure AI Search service.

## 4. How to Run the Local Environment

### Prerequisites
*   You must have **Docker** and **Docker Compose** installed on your system.

### Setup Steps
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd aximcyber
    ```
2.  **Create the environment file:**
    *   Copy the example environment file:
      ```bash
      cp .env.dev.example .env.dev
      ```
    *   Review the `.env.dev` file. No changes are needed to get started.

3.  **Build and Start the Services:**
    *   Use the following command to build the Docker images and start all services in the background:
      ```bash
      docker compose up -d --build
      ```

4.  **Run Initial Database Migrations:**
    *   Once the services are running, you need to apply the initial database migrations for the Django application:
      ```bash
      docker compose exec web python app/manage.py migrate
      ```

5.  **Create a Superuser (Optional):**
    *   To access the Django admin interface, create a superuser:
      ```bash
      docker compose exec web python app/manage.py createsuperuser
      ```

### Accessing Local Services
Once running, you can access the services at these URLs:

*   **Frontend Application:** [http://localhost:3000](http://localhost:3000)
*   **Backend API:** [http://localhost:8000/api/](http://localhost:8000/api/)
*   **Django Admin:** [http://localhost:8000/admin/](http://localhost:8000/admin/)
*   **MailHog (Email Viewer):** [http://localhost:8025](http://localhost:8025)
*   **ONLYOFFICE:** [http://localhost:8085](http://localhost:8085)
*   **Flower (Celery Monitor):** [http://localhost:5555](http://localhost:5555)