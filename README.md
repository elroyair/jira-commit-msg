# jira-commit-msg

[![tests](https://github.com/elroyair/jira-commit-msg/actions/workflows/main.yaml/badge.svg)](https://github.com/elroyair/jira-commit-msg/actions/workflows/main.yaml)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

A git [commit-msg hook](https://git-scm.com/docs/githooks#_commit_msg) to enforce branch naming and add issue IDs to commit messages.

This tool uses the [pre-commit](https://pre-commit.com/) framework.

## Purpose

- Extracts Jira issue ID from branch name and pre-pends it as `[ISSUE-123]` to your commit message
- Validates branch name and fails if it does not contain ticket ID (and optionally other configured prefixes)
- If atlassian URL is provided, issue will be validated to also exist

## Configuring for local use

With a repo that's already configured to use this hook, you may encounter an `Issue does not exist` error.

If the hook is configured with `atlassian_url`, you need your Atlassian personal access token. Create a `.env` file in your user home directory with:

```shell
JIRA_USER=user.name@company.com
JIRA_KEY=ABCDEFGHIJKLMNOP1234567890
```

Go your `Atlassian Account Management ⮕ Security ⮕ API Tokens` page [here](https://id.atlassian.com/manage-profile/security/api-tokens).

Select `Create API token`. Give it a name, copy the value, and paste it into the `.env` file we created above.

Should you configure a repository to with `atlassian_url`, you should probably add the above instructions to your repo README.

## Configuring for a repo

Create a `.jira-commit-msg-config.yaml` file at the root of your repo that looks something like this:

```yaml
atlassian_url: "https://company.atlassian.net"

excluded_branches:
  - "main"
  - "dev"
  - "release.*"

accepted_branch_prefixes:
  - "feature"
  - "hotfix"
  - "bugfix"
  - "sandbox"
  - "maintenance"
```

- On `excluded_branches`, the hook will not enforce anything or modify commit messages. It will always exit with success. Excluded branch filters are regular expressions, following the [re](https://docs.python.org/3/library/re.html) syntax.
- If there are any `accepted_branch_prefixes` defined, branches will have to appear as `prefix/ISSUE-123_friendly_description`, where prefix must be from the defined set.
- If there are no `accepted_branch_prefixes` defined, a valid branch will have to appear as `ISSUE-123_friendly_description`.
- Description text after the issue ID can be anything, and does not have to follow any particular syntax - snake case, kebab case, or whatever.
- A valid issue ID can contain any number of letters, followed by `-`, followed by any number of digits.
- If you do not want the script to validate that these tickets actually exist in Jira, you may omit the `atlassian_url` parameter.

Modify your `.pre-commit-config.yaml` as follows:

```yaml
default_install_hook_types: [pre-commit, commit-msg]
default_stages: [pre-commit]

repos:
  - repo: https://github.com/elroyair/jira-commit-msg
    rev: v0.9.0
    hooks:
      - id: jira-commit-msg
```

The `default` settings ensure that you install `commit-msg` hooks with `pre-commit install`, but also so that all hooks that do not specify `stage` do not install and run twice, once for `pre-commit` and then for `commit-msg`. Our hook is already configured to only run on `commit-msg`.

## Development

To test-run the hook, you may start `main.py` with parameters as follows:

```shell
poetry run jira-commit-msg commit-message-file branch_name path/to/.config-file -v
```

Where:

- `commit-message-file` - file to potentially prepend (mandatory)
- `branch_name` - optionally provide branch name, otherwise will be retrieved from Git
- `path/to/.config-file` - optionally provide path to config file, otherwise will be assumed to be `.jira-commit-msg-config.yaml` at Git repo root
- `-v` - optionally produce verbose output
