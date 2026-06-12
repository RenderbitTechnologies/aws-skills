import json
import logging
import os
import urllib.request
import urllib.error

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Maps CodePipeline name → Elastic Beanstalk environment name.
# The EB environment name is used as the GitHub status context path.
PIPELINE_TO_EB_ENV = {
    {{PIPELINE_TO_EB_ENV}}
}

PIPELINE_STATE_TO_GITHUB_STATE = {
    "STARTED": "pending",
    "RESUMED": "pending",
    "SUCCEEDED": "success",
    "FAILED": "failure",
    "CANCELED": "error",
    "STOPPED": "error",
}

GITHUB_REPO = "{{GITHUB_REPO}}"
AWS_REGION = os.environ["AWS_REGION"]
GITHUB_TOKEN_SSM_PARAM = os.environ["GITHUB_TOKEN_SSM_PARAM"]

codepipeline = boto3.client("codepipeline", region_name=AWS_REGION)
ssm = boto3.client("ssm", region_name=AWS_REGION)

_github_token_cache = None


def get_github_token() -> str:
    global _github_token_cache
    if _github_token_cache is None:
        response = ssm.get_parameter(Name=GITHUB_TOKEN_SSM_PARAM, WithDecryption=True)
        _github_token_cache = response["Parameter"]["Value"]
    return _github_token_cache


def get_commit_sha(pipeline_name: str, execution_id: str) -> str | None:
    response = codepipeline.get_pipeline_execution(
        pipelineName=pipeline_name,
        pipelineExecutionId=execution_id,
    )
    revisions = response.get("pipelineExecution", {}).get("artifactRevisions", [])
    if not revisions:
        return None
    return revisions[0].get("revisionId")


def get_console_url(pipeline_name: str, execution_id: str) -> str:
    return (
        f"https://{AWS_REGION}.console.aws.amazon.com/codesuite/codepipeline/pipelines"
        f"/{pipeline_name}/executions/{execution_id}/timeline?region={AWS_REGION}"
    )


def set_github_status(
    commit_sha: str,
    state: str,
    pipeline_name: str,
    execution_id: str,
    pipeline_state: str,
) -> None:
    eb_env = PIPELINE_TO_EB_ENV[pipeline_name]
    description_map = {
        "pending": f"Deploying to {eb_env}",
        "success": f"Deployed successfully to {eb_env}",
        "failure": f"Deployment failed on {eb_env}",
        "error": f"Deployment {pipeline_state.lower()} on {eb_env}",
    }

    payload = json.dumps(
        {
            "state": state,
            "target_url": get_console_url(pipeline_name, execution_id),
            "description": description_map.get(state, pipeline_name),
            "context": f"aws/elastic-beanstalk/{eb_env}",
        }
    ).encode("utf-8")

    url = f"https://api.github.com/repos/{GITHUB_REPO}/statuses/{commit_sha}"
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {get_github_token()}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "aws-codepipeline-status-lambda",
        },
    )

    try:
        with urllib.request.urlopen(req) as resp:
            logger.info("GitHub status set: sha=%s state=%s http=%s", commit_sha, state, resp.status)
    except urllib.error.HTTPError as e:
        logger.error("GitHub API error: %s %s", e.code, e.read().decode())
        raise


def lambda_handler(event: dict, context) -> None:
    logger.info("Event: %s", json.dumps(event))

    detail = event.get("detail", {})
    pipeline_name = detail.get("pipeline")
    execution_id = detail.get("execution-id")
    pipeline_state = detail.get("state")

    if pipeline_name not in PIPELINE_TO_EB_ENV:
        logger.info("Skipping unknown pipeline: %s", pipeline_name)
        return

    github_state = PIPELINE_STATE_TO_GITHUB_STATE.get(pipeline_state)
    if github_state is None:
        logger.info("Skipping unhandled pipeline state: %s", pipeline_state)
        return

    commit_sha = get_commit_sha(pipeline_name, execution_id)
    if not commit_sha:
        logger.warning("No artifact revision found for execution %s in pipeline %s", execution_id, pipeline_name)
        return

    logger.info(
        "Setting GitHub status: pipeline=%s state=%s -> github=%s sha=%s",
        pipeline_name,
        pipeline_state,
        github_state,
        commit_sha,
    )

    set_github_status(commit_sha, github_state, pipeline_name, execution_id, pipeline_state)
