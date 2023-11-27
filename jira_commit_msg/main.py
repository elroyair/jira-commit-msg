#!/usr/bin/env python

import os
import re
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

import argparse
import git
import yaml
from dotenv import load_dotenv
from jira import JIRA

SCRIPT_NAME = "jira-commit-msg"
CONFIG_FILE_NAME = f".{SCRIPT_NAME}-config.yaml"


@dataclass
class CommitMsgConfig:
    atlassian_url: str
    excluded_branches: list[str]
    accepted_branch_prefixes: list[str]
    branches_re: str

    def __init__(self, config_file_path: Path):
        self.atlassian_url = ""
        self.excluded_branches = []
        self.accepted_branch_prefixes = []
        self.branches_re = r"(\w+-\d+)"
        if config_file_path.is_file():
            with config_file_path.open("r") as file:
                repo_config = yaml.unsafe_load(file)
                if "atlassian_url" in repo_config.keys():
                    self.atlassian_url = repo_config["atlassian_url"]
                if "excluded_branches" in repo_config.keys():
                    self.excluded_branches = repo_config["excluded_branches"]
                if "accepted_branch_prefixes" in repo_config.keys():
                    self.accepted_branch_prefixes = repo_config[
                        "accepted_branch_prefixes"
                    ]
                    self.branches_re = (
                        "("
                        + "|".join(self.accepted_branch_prefixes)
                        + ")"
                        + r"\/"
                        + self.branches_re
                    )

    def is_branch_excluded(self, branch: str) -> bool:
        if len(self.excluded_branches) == 0:
            return True
        excl_branches_re = "(" + "|".join(self.excluded_branches) + ")"
        return re.match(excl_branches_re, branch) is not None

    def is_branch_valid(self, branch: str) -> bool:
        return re.match(self.branches_re, branch) is not None

    def extract_ticket_id(self, branch: str) -> str:
        if len(self.accepted_branch_prefixes) > 0:
            return re.match(self.branches_re, branch).group(2)
        return re.match(self.branches_re, branch).group(1)

    def validate_against_jira(
        self, issue_id: str, jira_user: str, jira_key: str
    ) -> bool:
        jira = JIRA(
            options={"server": f"{self.atlassian_url}", "rest_api_version": "3"},
            basic_auth=(jira_user, jira_key),
        )
        with suppress(Exception):
            issue = jira.issue(issue_id)
            return issue.key == issue_id
        return False


def enforce_hook(
    config: CommitMsgConfig, branch: str, commit_msg_filepath: Path
) -> int:
    if not config.is_branch_valid(branch):
        if config.is_branch_excluded(branch):
            print(f"{SCRIPT_NAME}: excluded branch `{branch}`")
            return 0
        else:
            print(f"{SCRIPT_NAME}: ERROR! Incorrect branch name `{branch}`\n"
                  f"    Should be prefix/ABC-123, where prefix is one of: {config.accepted_branch_prefixes}")
            return 1

    issue = config.extract_ticket_id(branch)

    print(f"{SCRIPT_NAME}: branch for issue `{issue}`")

    if len(config.atlassian_url) != 0:
        # To test script locally create a .env file with the following 2 values to
        # reflect your personal credentials
        if not config.validate_against_jira(
            issue_id=issue,
            jira_user=os.environ.get("JIRA_USER"),
            jira_key=os.environ.get("JIRA_KEY"),
        ):
            print(
                f"{SCRIPT_NAME}: ERROR! Issue {issue} does not exist at {config.atlassian_url}!"
            )
            return 1
    else:
        print(
            f"{SCRIPT_NAME}: No Atlassian URL provided, cannot confirm that the ticket exists"
        )

    with commit_msg_filepath.open("r+") as file:
        commit_msg = file.read()
        required_message = f"[{issue}]"
        if commit_msg.startswith(required_message):
            print(
                f"{SCRIPT_NAME}: commit message already starts with {required_message}"
            )
            return 0
        print(f"{SCRIPT_NAME}: prepending {required_message} to {commit_msg_filepath}")
        file.seek(0, 0)
        file.write(f"{required_message} {commit_msg}")
        return 0


def path_arg(path: str) -> Path:
    return Path(path).resolve()


def get_git_branch_name(root_search_path: Path) -> str:
    repo = git.Repo(root_search_path, search_parent_directories=True)
    return repo.active_branch.name


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Description.",
        usage="\n"
              "Usage",
        )
    parser.add_argument(
        "--verbose",
        "-v",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Verbose output",
    )
    parser.add_argument(
        "commit_message_file",
        type=path_arg,
        help="Path to commit message file, should always be passed in by pre-commit",
    )
    parser.add_argument(
        "git_branch",
        type=str,
        default=get_git_branch_name(Path.cwd()),
        help="Git branch",
    )
    parser.add_argument(
        "config_file_path",
        type=path_arg,
        default=Path.cwd() / CONFIG_FILE_NAME,
        help="Path to config file, should be in repo root when run by pre-commit",
    )
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])

    if args.verbose:
        print(
            f"commit_message_file={args.commit_message_file}\n"
            f"git_branch={args.git_branch}\n"
            f"config_file_path={args.config_file_path}"
        )

    config = CommitMsgConfig(args.config_file_path)
    if args.verbose:
        print(f"Config: {config}")

    sys.exit(
        enforce_hook(
            config=config, branch=args.git_branch, commit_msg_filepath=args.commit_message_file
        )
    )


if __name__ == "__main__":
    main()
