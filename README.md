# GH Monitor

Mini system that prevents orphan, not merged, branches from occuring.

## Authentication

The application expects a `GITHUB_TOKEN` env variable. It needs to be set prior to running `docker compose`.

The `GITHUB_TOKEN` env variable should contain a personal access token. The token should have at least read priviledges to all repositories.

## Needed information of Organization

### Number of opened branches

- Count branches per developer
  - Branch belongs to developer if the latest commit on this branch
    is done by this developer. This avoids making too many API requests, which is slow
- Sort it from newest to oldest and show relative time (e.g. 5 days, 2 months)
- Branches that are older than 1 week are yellow
- Branches that are older than 1 month are red
- Table for each developer: repo-name, branch-name, age

### Orphan branches

- Show all branches in all repos that belongs to developer that do
  not exist in organization

## Other

### Credentials

- Github token should be passed by env variable.

### Requirements

- [x] Create dockerfile and docker-compose - run as docker-compose
- [x] Use pipenv for dependance
- [x] Use ruff for linting
