# GH Monitor

Mini system that prevents orphan, not merged, branches to occur.

- [ ] use pyGithub
- [ ] grab some data
- [ ] display as static html website (only colored text to html)
      like here (https://mts3.aerob.it/mts3_reports/plan.html)

## Needed information of Organization

### Number of opened branches

- Count branches per developer
  - Branch belongs to developer if commit on this branch
    is done by this developer
- Sort it from newest to oldest and show relative time (e.g. 5 days, 2 months)
- Branches that are older than 1 week should be yellow
- Branches that are older than 1 month should be red
- Maybe table for each developer: repo-name, branch-name, age

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
