from flask import Flask, render_template
import github
import os
import github.Repository
from termcolor import colored
import atexit
import arrow
from functools import cache
import time
from concurrent import futures
from collections import Counter
from datetime import datetime


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
    except github.GithubException as e:
        print(f"Something went wrong: {e}")
        pass

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

    repo_branches = []

    with futures.ThreadPoolExecutor(max_workers=200) as executor:
        for i, repo in enumerate(repos):
            branches = repo.get_branches()
            repo_branches.append((repo, branches))
            # force pygitub to evaluate commit authors
            executor.map(lambda branch: branch.commit.author, branches)

    class Info:
        repo: github.Repository
        category: str
        issue_no: int | None
        issue: github.Issue.Issue | None
        issue_labels: list[str] | None
        branch_name: str
        last_commit_message: str
        last_commit_time: datetime
        time_ago: str
        color: str

    for repo, branches in repo_branches:
        # doesn't call the API to evaluate
        for branch in branches:
            if branch.name == repo.default_branch:
                continue
            # doesn't call the API to evaluate
            last_commit = branch.commit
            if last_commit.author not in open_branches:
                open_branches[last_commit.author] = []

            issue_no: int
            issue_number_separator = branch.name.find("-")
            if issue_number_separator == -1:
                issue_no = None
            else:
                try:
                    issue_no = int(branch.name[0:issue_number_separator])
                except ValueError:
                    issue_no = None

            record = Info()
            record.repo = repo
            record.category = None
            record.issue_no = issue_no
            record.branch_name = branch.name
            record.last_commit_message = last_commit.commit.message
            record.last_commit_time = last_commit.commit.committer.date
            open_branches[last_commit.author].append(record)

    def annotate_issue(record: Info):
        if record.issue_no is None:
            record.category = "Never linked"
        else:
            try:
                issue = record.repo.get_issue(record.issue_no)
                record.category = issue.state
                record.issue_labels = [issue.name for issue in issue.get_labels()]
            except github.GithubException:
                record.category = "Unlinked"

    with futures.ThreadPoolExecutor(max_workers=200) as executor:
        for author, records in open_branches.items():
            executor.map(annotate_issue, records)

    return open_branches


@cache
def search_orphaned_branches(org: github.Organization.Organization):
    # search for forks outside of organization
    repos = org.get_repos()
    members = org.get_members()

    orphan_record = []

    with futures.ThreadPoolExecutor(max_workers=200) as executor:
        forks_record = executor.map(lambda x: (x.name, list(x.get_forks())), repos)

    for repo, forks in forks_record:
        for fork in forks:
            try:
                name = fork.owner.login if hasattr(fork, "owner") else None
            except github.GithubException:
                name = None

            commits = fork.get_commits()
            try:
                last_commit_time = commits[0].commit.committer.date
                ago_str = arrow.get(last_commit_time).humanize()
            except github.GithubException:
                last_commit_time = "never"
            orphan_record.append([repo, name, ago_str])

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
            # accessing developer.login doesn't result in an API call
            developer.login
            if developer is not None and developer.login is not None
            else None,
            Counter([record.category for record in records]),
        )
        for developer, records in open_branches.items()
    ]
    return count_record


def convert_record_to_text(open_branches):
    open_branches_text = open_branches.copy()
    names = [
        developer.login
        if developer is not None and developer.login is not None
        else None
        for developer in open_branches.keys()
    ]
    for branches in open_branches_text.values():
        for branch in branches:
            branch.time_ago = arrow.get(branch.last_commit_time).humanize()
            date_diff = (arrow.utcnow() - branch.last_commit_time).days
            if date_diff > 30:
                branch.color = "tomato"
            elif date_diff > 7:
                branch.color = "goldenrod"
            else:
                branch.color = "black"
    open_branches_text = dict(
        map(lambda i, j: (i, j), names, open_branches_text.values())
    )

    return open_branches_text
