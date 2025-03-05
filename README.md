# Wagtail Sync

A Docker Compose project with two Wagtail CMS instances: Development and Production. This project allows content synchronization between the two instances.

## Features

- Two separate Wagtail CMS instances with MySQL databases
- Ability to sync entire database from dev to prod
- Ability to sync selected content from dev to prod
- Ability to sync media files from dev to prod
- Dashboard to monitor sync operations

## Project Structure

The project consists of:

- Development Wagtail instance (running on port 8001)
- Production Wagtail instance (running on port 8000)
- MySQL database for development instance
- MySQL database for production instance

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd wagtail-sync
   ```

2. Build and start the containers:
   ```
   docker-compose up -d
   ```

3. Wait for the containers to start and the initial migrations to complete.

4. Access the development instance at: http://localhost:8001/admin/
   - Default admin user: admin
   - Default password: admin

5. Access the production instance at: http://localhost:8000/admin/
   - Default admin user: admin
   - Default password: admin

## Usage

### Creating Content in Development

1. Log in to the development instance at http://localhost:8001/admin/
2. Create pages, images, and other content as needed.

### Syncing Content to Production

1. In the development instance, go to http://localhost:8001/sync/
2. Choose the type of sync you want to perform:
   - Full Database Sync: Syncs the entire database
   - Selected Content Sync: Syncs only selected pages
   - Media Files Sync: Syncs media files

3. For Selected Content Sync, you'll be prompted to select which pages to sync.
4. Click the sync button to start the sync process.
5. Monitor the sync status on the dashboard.

## Stopping the Service

To stop all containers:

```
docker-compose down
```

To stop and remove volumes (this will delete all data):

```
docker-compose down -v
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
