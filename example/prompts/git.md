# Gitea
- Git repos are stored on Gitea
- Gitea is accessible via http://host.docker.internal:3000 and/or your Gitea MCP tools
- When referencing PRs or other Gitea links (e.g. in chat), replace `host.docker.internal` with `localhost`.
- When interacting with Git you should use the Git cli, not the gitea tools for creating/editing files, if possible.
  - You can use other Gitea tools if needed such as listing repos, making PRs, and commenting on issues, READING files, etc, just avoid direct file manipulation through such tools.
- You should ALWAYS do your work on a branch and make a PR. Never commit to master/main.

# Workspace
- Note that humans and other agents dont have access to your workspace, so if you need to share files, do so via branches and PRs