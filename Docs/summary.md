# Wagtail Sync Project Summary

## Project Overview
Wagtail Sync is a project designed to manage and synchronize content between multiple Wagtail CMS instances. The project specifically focuses on maintaining production and development environments with synchronized content while allowing for independent development and testing.

## Technologies Used

### Core Technologies
- **Wagtail CMS**: A powerful content management system built on Django
- **Django**: Python web framework that forms the foundation of Wagtail
- **Python**: The primary programming language used throughout the project
- **MySQL**: Relational database system used for storing content and configuration

### Infrastructure
- **Docker**: Containerization platform used to create isolated environments
- **Docker Compose**: Tool for defining and running multi-container Docker applications
- **Git**: Version control system for tracking changes and collaborating

## Project Architecture

The project consists of two parallel Wagtail instances:

1. **Production Environment**
   - Primary content authoring environment
   - Runs on port 8000
   - Uses a dedicated MySQL database (wagtail_prod)

2. **Development Environment**
   - Testing and development environment
   - Runs on port 8001
   - Uses a separate MySQL database (wagtail_dev)

Both environments share the same codebase but use different settings modules and databases to maintain separation of concerns.

## Project Goals

1. **Content Synchronization**: Develop mechanisms to synchronize content from production to development environments
2. **Independent Development**: Allow developers to work in isolated environments without affecting production
3. **Consistent Deployment**: Ensure smooth transitions between development and production
4. **Data Integrity**: Maintain data consistency across environments
5. **Workflow Optimization**: Improve content management workflows for teams working with Wagtail

## Project Structure

- **app/**: Contains the Django/Wagtail application code
  - **wagtail_project/**: Main project settings and configuration
  - **templates/**: HTML templates for the site
  - **static/**: Static assets (CSS, JS, images)
  - **media/**: User-uploaded content
  - **staticfiles/**: Collected static files for production

- **Docker Configuration**:
  - **Dockerfile**: Defines the application container
  - **docker-compose.yml**: Orchestrates the multi-container setup

## Development Workflow

1. Content is created and managed in the production environment
2. Developers can sync content from production to development as needed
3. Code changes are made and tested in the development environment
4. Once approved, code changes are deployed to production

This architecture allows for a clean separation between content management and code development, making it easier to maintain and evolve the website over time. 