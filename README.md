# Stocks Serverless Pipeline

A fully automated serverless system that identifies the top-moving stock each day from a tech watchlist, stores the results in DynamoDB, and displays the history on a public dashboard.

**Live site:** [https://d35rzcnd1ox0a5.cloudfront.net](https://d35rzcnd1ox0a5.cloudfront.net)
**API endpoint:** [https://i9gve0bcj0.execute-api.us-east-1.amazonaws.com/prod/movers](https://i9gve0bcj0.execute-api.us-east-1.amazonaws.com/prod/movers)

## Watchlist

`AAPL` · `MSFT` · `GOOGL` · `AMZN` · `TSLA` · `NVDA`

## Architecture

```
EventBridge (6 AM ET, weekdays)
        │
        ▼
  Ingestion Lambda ──► Massive API (Grouped Daily)
        │                     │
        │              (403? schedule retry
        │               via EventBridge Scheduler,
        │               30 min intervals, max 8)
        ▼
    DynamoDB (stock-movers)
        ▲
        │
    API Lambda ◄── API Gateway (GET /movers?days=7)
        │               │
        │         Cache-Control: max-age=3600
        │               │
        ▼               ▼
                CloudFront + S3 (React SPA)
```

| Layer       | Technology                     |
|-------------|--------------------------------|
| IaC         | AWS CDK (Python)               |
| Backend     | Python 3.12 (AWS Lambda)       |
| Data Store  | DynamoDB (PAY_PER_REQUEST)     |
| API         | API Gateway (REST)             |
| Frontend    | React 19 + TypeScript (Vite)   |
| Hosting     | CloudFront + S3                |
| Charts      | Recharts                       |
| Secrets     | SSM Parameter Store            |
| Stock Data  | Massive API (Grouped Daily)    |
| CI/CD       | GitHub Actions                 |

## Project Structure

```
├── backend/
│   └── lambdas/
│       ├── ingestion/handler.py   # Daily cron — fetches stock data, finds top mover
│       └── api/handler.py         # GET /movers — returns last N days from DynamoDB
├── frontend/                      # Vite + React + TypeScript
│   └── src/
│       ├── App.tsx                # Full dashboard: stats, chart, sparklines, day rows
│       ├── hooks/useMovers.ts     # Data fetching hook with retry support
│       ├── types/index.ts         # Mover and Stock interfaces
│       └── index.css              # All styles (dark theme)
├── infra/                         # AWS CDK (Python)
│   ├── app.py
│   ├── cdk.json
│   ├── deploy.sh                  # One-command full deployment
│   ├── requirements.txt
│   └── stacks/
│       ├── pipeline_stack.py      # Composes all constructs
│       └── constructs/
│           ├── database.py        # DynamoDB table
│           ├── ingestion.py       # Lambda + EventBridge + Scheduler IAM + SSM
│           ├── api.py             # Lambda + API Gateway
│           └── frontend.py        # S3 + CloudFront + BucketDeployment
└── .github/workflows/deploy.yml   # CI/CD — auto-deploys on push to main
```

## How It Works

1. **EventBridge** triggers the Ingestion Lambda at 11 AM UTC (6 AM ET) on weekdays.
2. **Ingestion Lambda** targets the **previous trading day** (free-tier data is available one day after close). It calls the Massive Grouped Daily endpoint for all US stocks, filters to the watchlist, calculates `((close - open) / open) * 100` for each, and writes the top mover (highest absolute % change) plus all 6 stocks to DynamoDB.
3. **Retry on 403**: If the data isn't published yet, the Lambda schedules a retry via **EventBridge Scheduler** — 30-minute intervals, up to 8 attempts (4 hours). The one-time schedule auto-deletes after firing.
4. **API Lambda** serves `GET /movers` via API Gateway with:
   - `?days=N` query parameter (default 7, max 30)
   - `Cache-Control: public, max-age=3600` header
   - Proper status codes: `200` with data, `204` when empty, `500` with structured error body
   - CORS headers for cross-origin requests
5. **React SPA** on S3/CloudFront displays:
   - Summary stats (period, average move, green/red day ratio)
   - Recharts bar chart of daily top movers, color-coded per ticker
   - Per-ticker sparklines with win counts
   - Expandable day rows (collapsed: winner + % change; expanded: all 6 stocks)
   - Loading skeleton and error state with retry button

## Deployment

### Prerequisites

- AWS CLI configured with a Free Tier account (`aws sts get-caller-identity` should work)
- AWS CDK CLI: `npm install -g aws-cdk`
- Node.js >= 20
- Python >= 3.9
- Massive API key — [sign up at massive.com](https://massive.com) (free, no credit card)

### First-Time Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/stocks-serverless-pipeline.git
cd stocks-serverless-pipeline

# 2. Create .env with your Massive API key
echo "MASSIVE_API_KEY=your_key_here" > .env

# 3. Bootstrap CDK (one-time per AWS account/region)
cd infra
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

# 4. Deploy everything
./deploy.sh
```

The `deploy.sh` script handles all 5 steps automatically:
1. Validates AWS credentials, CDK CLI, and API key
2. Stores the API key in SSM Parameter Store (SecureString)
3. Installs Python dependencies in a virtualenv
4. Builds the frontend (`npm install && npm run build`)
5. Runs `cdk deploy` — creates all AWS resources, uploads frontend to S3, invalidates CloudFront

On success it prints the **Site URL** and **API URL**.

### Subsequent Deploys

**Infrastructure changes** (new resources, IAM, schedule changes):
```bash
cd frontend && npm run build && cd ../infra && source .venv/bin/activate && cdk deploy --require-approval never
```

**Code-only changes** (Lambda handlers, frontend UI): just push to `main`. GitHub Actions automatically:
1. Updates both Lambda functions (zip + `update-function-code`)
2. Builds the frontend
3. Syncs to S3 and invalidates CloudFront
4. Backfills the last 7 trading days of data
5. Runs a smoke test (`curl` the API, assert HTTP 200)

### Frontend-Only Rebuild

If you only changed frontend code and want to update the live site without a full CDK deploy:
```bash
cd frontend && npm run build
aws s3 sync dist/ s3://stockspipeline-frontendsitebucket177cee8f-gsne74ksgqoq/ --delete
aws cloudfront create-invalidation --distribution-id E32TXO69X8CTFS --paths "/*"
```

### GitHub Actions Setup

Add these secrets in **Settings > Secrets and variables > Actions**:

| Secret                  | Value                          |
|-------------------------|--------------------------------|
| `AWS_ACCESS_KEY_ID`     | Your IAM access key            |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret key            |

The Massive API key is stored in SSM Parameter Store (set during `deploy.sh`), not as a GitHub secret.

### Manual Testing

```bash
# Invoke the ingestion Lambda for a specific date
aws lambda invoke \
  --function-name StocksPipeline-IngestionHandler7867F31D-bGQA75Rgd4JM \
  --payload '{"date": "2026-03-05"}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/out.json && cat /tmp/out.json

# Query the API (default 7 days)
curl https://i9gve0bcj0.execute-api.us-east-1.amazonaws.com/prod/movers

# Query with custom range
curl https://i9gve0bcj0.execute-api.us-east-1.amazonaws.com/prod/movers?days=14

# Scan DynamoDB directly
aws dynamodb scan --table-name StocksPipeline-DatabaseMoversTable* --region us-east-1
```

### Tear Down

```bash
cd infra
source .venv/bin/activate
cdk destroy
```

This removes all AWS resources (Lambda, DynamoDB, API Gateway, S3, CloudFront, IAM roles, EventBridge rules). The SSM parameter must be deleted separately:
```bash
aws ssm delete-parameter --name /stocks-pipeline/massive-api-key --region us-east-1
```

## Separation of Concerns

- **Ingestion Lambda** handles only data collection: API calls, percentage calculation, and DynamoDB writes. Triggered by EventBridge on a cron schedule. Has DynamoDB write + SSM read permissions.
- **API Lambda** handles only data retrieval: reads from DynamoDB and returns JSON with caching headers. Triggered by API Gateway. Has DynamoDB read-only permissions.
- **CDK constructs** are modular: `database.py`, `ingestion.py`, `api.py`, and `frontend.py` each manage their own resources and can be modified independently.

## Error Handling

- **Rate limiting (429)**: Ingestion Lambda retries up to 3 times with exponential backoff.
- **Server errors (5xx)**: Retries with backoff, same as rate limiting.
- **Data not available (403)**: Free-tier data is published one calendar day after close. On 403, the Lambda schedules a retry via EventBridge Scheduler (30 min intervals, max 8 attempts / 4 hours). The schedule auto-deletes after execution.
- **Weekends**: `get_trading_date()` targets the previous trading day, skipping weekends automatically.
- **Zero open price**: Stocks with a zero open price are skipped to avoid division-by-zero.
- **API Lambda failures**: Returns structured JSON with `500` status code and `{"error": "...", "message": "..."}` body.
- **Empty data**: API returns `204 No Content` when no mover data exists for the requested range.
- **Frontend**: Loading skeleton during fetch, error state with retry button on failure, graceful handling of `204` responses.

## Security

- Massive API key stored in **SSM Parameter Store** as a SecureString (KMS encrypted at rest).
- `.gitignore` excludes `.env`, `cdk-outputs.json`, and `cdk.out/`.
- Lambda IAM roles follow **least privilege**: ingestion gets DynamoDB write + SSM read + Scheduler create; API gets DynamoDB read only.
- No AWS credentials or API keys in source code.

## Trade-offs

- **Free-tier Polygon API** — Data is one trading day behind. We compensate with `get_trading_date()` targeting yesterday and a retry mechanism for edge cases. A paid plan would give same-day data after market close.
- **DynamoDB Scan** — The table holds at most ~260 rows/year (weekdays only). A Scan with limit and in-memory sort is simpler than maintaining a GSI for what is effectively a tiny dataset.
- **Grouped Daily endpoint** — One API call fetches all ~12,000 US stocks instead of 6 individual calls, staying well within the free tier limit of 5 requests/minute.
- **EventBridge Scheduler retries vs Step Functions** — Scheduler is one API call to create a delayed re-invocation. Step Functions would give a visual workflow and built-in retry policies, but adds a state machine definition for what is simple "try again in 30 min" logic.
- **Cache-Control: 1 hour** — Data changes once per day, so a 1-hour browser/CDN cache reduces Lambda invocations with minimal staleness. Could be increased to 6 hours safely.
- **Single CDK stack** — Simpler to deploy and tear down than multi-stack. Modularity comes from separate CDK Construct classes.
- **GitHub Actions CI/CD** — Pushes update Lambda code via zip + `update-function-code` rather than a full CDK deploy, reducing deploy time from ~5 minutes to ~30 seconds. Full CDK deploy is only needed for infrastructure changes.
- **No Lambda Layer** — Both handlers use only stdlib + boto3 (included in the Lambda runtime), so no external dependencies or layer management needed.
