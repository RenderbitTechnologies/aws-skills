---
name: codepipeline-github-status-setup
description: >
  Sets up GitHub commit status checks for AWS CodePipeline → Elastic Beanstalk deployments.
  Creates a Lambda + EventBridge + CloudFormation stack that automatically marks commits as
  pending/success/failure as deployments progress. Use this skill whenever the user wants to
  connect CodePipeline to GitHub commit statuses, add deployment status badges on commits,
  integrate AWS deployments with GitHub PR checks, or set up pipeline→GitHub status webhooks.
  Invoke it even if the user just says "I want to see deployment status on my commits" or
  "can GitHub show me when a deploy is running".
---

# CodePipeline → GitHub Commit Status Setup

This skill provisions infrastructure that automatically posts GitHub commit statuses when
CodePipeline deployments start, succeed, or fail — giving a clear per-environment visual on
every commit without any manual work after the initial setup.

**What gets created:**
- `aws/codepipeline-github-status/lambda_function.py` — Python 3.12 Lambda
- `aws/codepipeline-github-status/template.yml` — CloudFormation (IAM role, Lambda, EventBridge rule, Log Group)
- `aws/codepipeline-github-status/deploy.sh` — packages and deploys everything
- SSM SecureString for the GitHub token
- A CloudFormation stack managing all resources under a consistent prefix

---

## Step 1 — Collect inputs

Ask the user for all of the following before generating any files. Do not proceed until you
have confirmed values for everything.

| # | Input | Example |
|---|-------|---------|
| 1 | **GitHub Personal Access Token** | `github_pat_...` or `ghp_...` |
| 2 | **GitHub repository** (`owner/repo`) | `myorg/my-app` |
| 3 | **AWS CLI profile** | `myprofile` |
| 4 | **AWS region** | `ap-south-1` |
| 5 | **Resource name prefix** (kebab-case, no trailing dash) | `my-project` |
| 6 | **SSM parameter path** for the token | `/my-project/github-token` |
| 7 | **Pipeline mappings** — one row per pipeline: pipeline name → EB environment name | see below |

For the **pipeline mappings**, prompt the user to list each CodePipeline by name and its
matching Elastic Beanstalk environment name. The pipeline name and EB environment name are
often identical, but ask explicitly — they can differ. Collect until the user says they're done.

Example confirmed summary to show the user before proceeding:

```
GitHub repo:    myorg/my-app
AWS profile:    myprofile
AWS region:     ap-south-1
Prefix:         my-project
SSM path:       /my-project/github-token

Pipeline → EB environment:
  my-app-prod    → my-app-prod
  my-app-staging → my-app-staging
  my-app-worker  → my-app-worker
```

---

## Step 2 — Generate the files

Read the three templates from this skill's `templates/` directory (use the Read tool).
Generate the real files into `aws/codepipeline-github-status/` in the project root, substituting
the user's values everywhere a `{{PLACEHOLDER}}` appears.

### Template → generated file mapping

| Template | Output path |
|----------|-------------|
| `templates/lambda_function.py` | `aws/codepipeline-github-status/lambda_function.py` |
| `templates/template.yml` | `aws/codepipeline-github-status/template.yml` |
| `templates/deploy.sh` | `aws/codepipeline-github-status/deploy.sh` |

### Placeholder substitution guide

**`lambda_function.py`**

- `{{GITHUB_REPO}}` → `owner/repo` string (e.g., `myorg/my-app`)
- `{{PIPELINE_TO_EB_ENV}}` → Python dict literal, one entry per pipeline:
  ```python
      "my-app-prod": "my-app-prod",
      "my-app-staging": "my-app-staging",
  ```

**`template.yml`**

- `{{PREFIX}}` → resource prefix (e.g., `my-project`) — appears in RoleName, FunctionName, EventBridge Name
- `{{SSM_PARAM_PATH}}` → the SSM parameter path
- `{{PIPELINE_NAMES_YAML_LIST}}` → YAML sequence items, one per pipeline:
  ```yaml
            - my-app-prod
            - my-app-staging
  ```

**`deploy.sh`**

- `{{AWS_PROFILE}}` → AWS CLI profile
- `{{AWS_REGION}}` → AWS region
- `{{PREFIX}}` → resource prefix
- `{{SSM_PARAM_PATH}}` → SSM parameter path

After writing the files, make `deploy.sh` executable:
```bash
chmod +x aws/codepipeline-github-status/deploy.sh
```

---

## Step 3 — Store the GitHub token in SSM

```bash
aws ssm put-parameter \
  --profile <AWS_PROFILE> \
  --region <AWS_REGION> \
  --name <SSM_PARAM_PATH> \
  --type SecureString \
  --value "<TOKEN>" \
  --description "GitHub PAT for CodePipeline commit status checks" \
  --overwrite
```

Do **not** echo the raw token value in any output shown to the user.

---

## Step 4 — Deploy

```bash
cd aws/codepipeline-github-status && ./deploy.sh
```

The deploy script:
1. Zips `lambda_function.py`
2. Runs `cloudformation deploy` (creates the stack on first run, updates on subsequent runs)
3. Calls `lambda update-function-code` to push the real code (replaces the CloudFormation placeholder)
4. Waits for the Lambda update to settle

---

## Step 5 — Verify

Confirm the EventBridge rule is wired to the Lambda and the SSM env var is correct:

```bash
aws events list-targets-by-rule \
  --profile <AWS_PROFILE> \
  --region <AWS_REGION> \
  --rule <PREFIX>-codepipeline-github-status-trigger \
  --query 'Targets[*].[Id,Arn]' \
  --output table

aws lambda get-function-configuration \
  --profile <AWS_PROFILE> \
  --region <AWS_REGION> \
  --function-name <PREFIX>-codepipeline-github-status \
  --query 'Environment.Variables' \
  --output table
```

---

## What the user sees on GitHub

Each commit on a covered branch will show one check **per EB environment**:

- **Context**: `aws/elastic-beanstalk/<eb-environment-name>`
- **Pending**: "Deploying to `<eb-env>`" (links to the CodePipeline execution timeline)
- **Success**: "Deployed successfully to `<eb-env>`"
- **Failure / Error**: "Deployment failed on `<eb-env>`"

`SUPERSEDED` pipeline state is intentionally not handled — CodePipeline fires it when a newer
execution replaces a queued one, and the replacement execution will post the final status.

---

## Re-deploying / updating later

To push Lambda code changes or update the CloudFormation stack after editing files, just
re-run `./deploy.sh` from `aws/codepipeline-github-status/`. It is fully idempotent.
