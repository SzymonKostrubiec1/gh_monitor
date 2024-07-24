from flask import Flask, render_template
import github
import os
from termcolor import colored
import atexit
import arrow
from functools import cache
import time


def create_app():
    app = Flask(__name__)

    try:
        token: str = os.environ["GITHUB_TOKEN"]
    except KeyError:
        print(colored("GITHUB_TOKEN environment variable unset", "red"))
        exit(1)
    token = github.Auth.Token(token)
    github_connection = github.Github(auth=token)
    try:
        # make an API call to determine whether authorization was successful
        login = github_connection.get_user().login
    except github.GithubException.BadCredentialsException:
        print(colored("Provided token is invalid", "red"))
        exit(1)

    atexit.register(lambda: github_connection.close())

    name = github_connection.get_user().name
    name = name if name is not None else login

    org = github_connection.get_organization("Aerobits")

    @app.route("/")
    def index():
        start = time.time()
        open_branches = get_open_branches(org)
        elapsed = time.time() - start
        branches_count = count_open_branches_per_developer(open_branches)
        open_branches_text = convert_record_to_text(open_branches)
        # prepare text for display
        return render_template(
            "index.html",
            user_name=name,
            org_name=org.login,
            open_branches=open_branches_text,
            branches_count=branches_count,
            time=round(elapsed, 2),
        )

    @app.route("/orphans.html")
    def orphans():
        start = time.time()
        orphan_record, members_repo_record = search_orphaned_branches(org)
        elapsed = time.time() - start
        return render_template(
            "orphans.html",
            org_name=org.login,
            orphan_record=orphan_record,
            members_repo_record=members_repo_record,
            time=round(elapsed, 2),
        )

    return app


@cache
def get_open_branches(org: github.Organization.Organization):
    repos = org.get_repos()

    open_branches = dict()

    for i, repo in enumerate(repos):
        print(f"Got information from {i} repositories")
        print(repo.name)
        branches = repo.get_branches()
        for branch in branches:
            if branch.name == repo.default_branch:
                continue
            last_commit = branch.commit
            if last_commit.author not in open_branches:
                open_branches[last_commit.author] = []
            open_branches[last_commit.author].append(
                [
                    repo,
                    branch.name,
                    last_commit.commit.message,
                    last_commit.commit.committer.date,
                ]
            )

    return open_branches


@cache
def search_orphaned_branches(org: github.Organization.Organization):
    # search for forks outside of organization
    repos = org.get_repos()
    members = (
        org.get_members()
    )  # FIXME: organization has no public members, no way to test

    orphan_record = []

    for repo in repos:
        for fork in repo.get_forks():
            if True:  #  fork.owner in members: # FIXME
                name = (
                    fork.owner.name if fork.owner.name is not None else fork.owner.login
                )
                commits = fork.get_commits()
                last_commit_time = commits[0].commit.committer.date
                ago_str = arrow.get(last_commit_time).humanize()
                orphan_record.append([repo.name, name, ago_str])

    members_repo_record = []
    # list public repositories beloning to organization members
    for member in members:
        for repo in member.get_repos():
            name = member.name if member.name is not None else member.login
            members_repo_record.append([name, repo.name])

    return orphan_record, members_repo_record


def count_open_branches_per_developer(open_branches):
    count_record = [
        (
            developer.name
            if developer is not None and developer.name is not None
            else developer.login
            if developer is not None and developer.login is not None
            else None,
            len(branches),
        )
        for developer, branches in open_branches.items()
    ]
    count_record.sort(key=lambda record: record[1], reverse=True)
    return count_record


def convert_record_to_text(open_branches):
    open_branches_text = open_branches.copy()
    names = [
        developer.name
        if developer is not None and developer.name is not None
        else developer.login
        if developer is not None and developer.login is not None
        else None
        for developer in open_branches.keys()
    ]
    for branches in open_branches_text.values():
        branches.sort(key=lambda branch: branch[3], reverse=True)
        for branch in branches:
            date = branch[3]
            branch.append(arrow.get(date).humanize())
            if (arrow.utcnow() - date).days > 30:
                color = "tomato"
            elif (arrow.utcnow() - date).days > 7:
                color = "goldenrod"
            else:
                color = "black"
            branch.append(color)

    open_branches_text = zip(names, open_branches_text.values())

    return open_branches_text
