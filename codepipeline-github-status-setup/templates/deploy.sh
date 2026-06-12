#!/usr/bin/env bash
# Deploys (or updates) the CodePipeline → GitHub status Lambda stack.
# Re-run this script any time you change lambda_function.py or template.yml.
set -euo pipefail

PROFILE="{{AWS_PROFILE}}"
REGION="{{AWS_REGION}}"
STACK_NAME="{{PREFIX}}-codepipeline-github-status"
LAMBDA_FUNCTION="{{PREFIX}}-codepipeline-github-status"
SSM_PARAM="{{SSM_PARAM_PATH}}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(mktemp -d)"
ZIP_PATH="${PACKAGE_DIR}/function.zip"

echo "==> Packaging Lambda function..."
cp "${SCRIPT_DIR}/lambda_function.py" "${PACKAGE_DIR}/"
(cd "${PACKAGE_DIR}" && zip -q function.zip lambda_function.py)
echo "    Packaged: ${ZIP_PATH}"

echo "==> Deploying CloudFormation stack '${STACK_NAME}'..."
aws cloudformation deploy \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --template-file "${SCRIPT_DIR}/template.yml" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides GitHubTokenSsmParam="${SSM_PARAM}" \
  --no-fail-on-empty-changeset

echo "==> Updating Lambda function code..."
aws lambda update-function-code \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${LAMBDA_FUNCTION}" \
  --zip-file "fileb://${ZIP_PATH}" \
  --output text \
  --query 'FunctionArn'

echo "==> Waiting for Lambda update to complete..."
aws lambda wait function-updated \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --function-name "${LAMBDA_FUNCTION}"

rm -rf "${PACKAGE_DIR}"

echo ""
echo "Done. Stack outputs:"
aws cloudformation describe-stacks \
  --profile "${PROFILE}" \
  --region "${REGION}" \
  --stack-name "${STACK_NAME}" \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table
