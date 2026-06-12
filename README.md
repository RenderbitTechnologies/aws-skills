# AWS Skills

AI agent skills for deploying and managing infrastructure on Amazon Web Services.

## Skills

### [`codepipeline-github-status-setup`](./codepipeline-github-status-setup/SKILL.md)

Sets up GitHub commit status checks for AWS CodePipeline → Elastic Beanstalk deployments.

| Component | Detail |
|---|---|
| Trigger | EventBridge rule on CodePipeline execution state changes |
| Handler | Python 3.12 Lambda function |
| Secret storage | SSM Parameter Store (SecureString) |
| Infrastructure | CloudFormation stack (IAM role, Lambda, EventBridge rule, Log Group) |
| GitHub integration | Statuses API — `aws/elastic-beanstalk/<env>` context per pipeline |

**Covers the full lifecycle:**

- Phase 1 — Collect inputs (GitHub token, repo, AWS profile, region, resource prefix, pipeline mappings)
- Phase 2 — Generate infrastructure files (`lambda_function.py`, `template.yml`, `deploy.sh`)
- Phase 3 — Store GitHub PAT in SSM Parameter Store
- Phase 4 — Deploy CloudFormation stack and upload Lambda code
- Phase 5 — Verify EventBridge → Lambda wiring

Each covered commit shows one status check per environment — `pending` while deploying, `success` or `failure` on completion — linking directly to the CodePipeline execution timeline in the AWS console.

## Installation

### Via skills CLI (recommended)

```bash
npx skills add UEM-Group-Websites/aws-skills
```

### From a release (manual)

Download the `.skill` file for a specific skill from the [Releases](https://github.com/UEM-Group-Websites/aws-skills/releases) page, then install it:

```bash
# Example for codepipeline-github-status-setup
unzip codepipeline-github-status-setup.skill -d ~/.agents/skills/
ln -s "../../.agents/skills/codepipeline-github-status-setup" \
      ~/.claude/skills/codepipeline-github-status-setup
```

### Claude Code (manual)

```bash
# 1. Clone this repo
git clone https://github.com/UEM-Group-Websites/aws-skills.git /tmp/aws-skills

# 2. Copy the skill(s) you want
mkdir -p ~/.agents/skills/codepipeline-github-status-setup
cp -r /tmp/aws-skills/codepipeline-github-status-setup/. \
      ~/.agents/skills/codepipeline-github-status-setup/

# 3. Create the symlink Claude Code needs
ln -s "../../.agents/skills/codepipeline-github-status-setup" \
      ~/.claude/skills/codepipeline-github-status-setup
```

Restart Claude Code — the skill will appear automatically.

## Usage

Once installed, trigger the skill by telling Claude Code something like:

- *"Set up GitHub commit status checks for my CodePipeline deployments"*
- *"Add deployment status badges to our GitHub commits from CodePipeline"*
- *"I want to see pending/success/failure on commits when Elastic Beanstalk deploys"*
- *"Wire up CodePipeline to the GitHub Statuses API"*

Claude will walk you through each phase, collecting your project's real values for every placeholder before generating and deploying anything.

## Repository layout

```
aws-skills/
└── codepipeline-github-status-setup/
    ├── SKILL.md                  # Skill instructions and input collection workflow
    └── templates/
        ├── lambda_function.py    # Python Lambda template
        ├── template.yml          # CloudFormation template
        └── deploy.sh             # Package and deploy script
```

## Releases

Tagged releases (e.g. `v1.0.0`) automatically package every skill as a `.skill` file and attach it to the [GitHub Release](https://github.com/UEM-Group-Websites/aws-skills/releases). A `.skill` file is a standard zip archive — you can inspect or extract it with any zip tool.

## License

MIT
