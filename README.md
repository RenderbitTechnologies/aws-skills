# AWS Skills

A collection of skills for AI coding agents (Claude Code and compatible tools) that streamline common AWS cloud workflows — turning multi-step infrastructure tasks into guided, parameterised conversations.

## Skills

### [`codepipeline-github-status-setup`](./codepipeline-github-status-setup/SKILL.md)

Sets up GitHub commit status checks for AWS CodePipeline → Elastic Beanstalk deployments.

Provisions a Lambda function triggered by EventBridge that automatically marks commits as `pending`, `success`, or `failure` as deployments progress through CodePipeline. All AWS resources (Lambda, IAM role, EventBridge rule, CloudWatch Log Group) are deployed via a CloudFormation stack and prefixed with a configurable name to avoid collisions across projects.

When invoked, the skill collects your GitHub token, repository, AWS profile, region, resource prefix, and pipeline-to-environment mappings, then generates and deploys everything end-to-end.
