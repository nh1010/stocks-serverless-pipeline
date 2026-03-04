#!/bin/bash
# Stocks Pipeline Deployment Script
# Deploys the full CDK stack: DynamoDB, Lambdas, API Gateway, S3, CloudFront
#
# Prerequisites:
#   - AWS CLI configured (aws sts get-caller-identity)
#   - AWS CDK CLI installed (npm install -g aws-cdk)
#   - Python 3.9+ with venv
#   - Node.js 20+
#   - .env file with MASSIVE_API_KEY at project root
#
# Usage:
#   cd infra && ./deploy.sh
#
# NOTE: CDK bootstrap is a one-time manual step. See README.md.

set -e

REGION="us-east-1"
SSM_PARAM_NAME="/stocks-pipeline/massive-api-key"
STACK_NAME="StocksPipeline"
INFRA_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$INFRA_DIR/.." && pwd)"

echo "============================================"
echo "  Stocks Pipeline — Deploy"
echo "============================================"
echo "Region:  $REGION"
echo "Stack:   $STACK_NAME"
echo ""

# ── 0. Preflight checks ──────────────────────────────────────────────

echo "[0/5] Preflight checks..."

if ! aws sts get-caller-identity &>/dev/null; then
  echo "ERROR: AWS CLI not configured. Run 'aws configure' first."
  exit 1
fi
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "  AWS Account: $ACCOUNT_ID"

if ! command -v cdk &>/dev/null; then
  echo "ERROR: CDK CLI not found. Run 'npm install -g aws-cdk'."
  exit 1
fi
echo "  CDK CLI:     $(cdk --version 2>/dev/null | head -1)"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  echo "ERROR: .env file not found. Create it with MASSIVE_API_KEY=your_key"
  exit 1
fi

MASSIVE_API_KEY=$(grep MASSIVE_API_KEY "$PROJECT_ROOT/.env" | cut -d '=' -f2)
if [ -z "$MASSIVE_API_KEY" ]; then
  echo "ERROR: MASSIVE_API_KEY not found in .env"
  exit 1
fi
echo "  API Key:     ***${MASSIVE_API_KEY: -4}"
echo ""

# ── 1. Store API key in SSM Parameter Store ───────────────────────────

echo "[1/5] Storing API key in SSM Parameter Store..."

if aws ssm get-parameter --name "$SSM_PARAM_NAME" --region "$REGION" &>/dev/null; then
  echo "  Parameter already exists — updating..."
  aws ssm put-parameter \
    --name "$SSM_PARAM_NAME" \
    --value "$MASSIVE_API_KEY" \
    --type SecureString \
    --overwrite \
    --region "$REGION" \
    --output text --query Version
else
  echo "  Creating new parameter..."
  aws ssm put-parameter \
    --name "$SSM_PARAM_NAME" \
    --value "$MASSIVE_API_KEY" \
    --type SecureString \
    --region "$REGION" \
    --output text --query Version
fi
echo "  Done."
echo ""

# ── 2. Install CDK Python dependencies ────────────────────────────────

echo "[2/5] Installing CDK dependencies..."
cd "$INFRA_DIR"

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo "  Done."
echo ""

# ── 3. Build frontend (if package.json exists) ───────────────────────

echo "[3/5] Building frontend..."

if [ -f "$PROJECT_ROOT/frontend/package.json" ]; then
  cd "$PROJECT_ROOT/frontend"
  npm install --silent
  npm run build
  echo "  Built frontend/dist/"
else
  echo "  No frontend/package.json — using placeholder."
  mkdir -p "$PROJECT_ROOT/frontend/dist"
  if [ ! -f "$PROJECT_ROOT/frontend/dist/index.html" ]; then
    echo '<html><body><h1>Stock Movers — deploying soon</h1></body></html>' \
      > "$PROJECT_ROOT/frontend/dist/index.html"
  fi
fi
echo ""

# ── 4. Deploy CDK stack ──────────────────────────────────────────────

echo "[4/5] Deploying CDK stack (this may take 3-5 min on first deploy)..."
cd "$INFRA_DIR"
source .venv/bin/activate

JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 \
  cdk deploy "$STACK_NAME" \
  --require-approval never \
  --outputs-file "$PROJECT_ROOT/cdk-outputs.json" \
  2>&1

echo "  Done."
echo ""

# ── 5. Print outputs ─────────────────────────────────────────────────

echo "[5/5] Stack outputs:"
echo ""

if [ -f "$PROJECT_ROOT/cdk-outputs.json" ]; then
  API_URL=$(python3 << PYEOF
import json
d = json.load(open("$PROJECT_ROOT/cdk-outputs.json"))
print(d.get("$STACK_NAME", {}).get("ApiUrl", ""))
PYEOF
  )
  SITE_URL=$(python3 << PYEOF
import json
d = json.load(open("$PROJECT_ROOT/cdk-outputs.json"))
print(d.get("$STACK_NAME", {}).get("SiteUrl", ""))
PYEOF
  )

  echo "  API URL:  $API_URL"
  echo "  Site URL: $SITE_URL"
  echo ""
  echo "Test commands:"
  echo "  curl ${API_URL}movers"
  echo "  aws lambda invoke --function-name $STACK_NAME-IngestionHandler --region $REGION /tmp/out.json && cat /tmp/out.json"
else
  echo "  (outputs file not found — check CDK deploy output above)"
fi

echo ""
echo "============================================"
echo "  Deploy complete!"
echo "============================================"
