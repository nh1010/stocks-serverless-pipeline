# Stocks Serverless Pipeline

A fully automated serverless system that identifies the top-moving stock each day from a tech watchlist, stores the results in DynamoDB, and displays the history on a public website.

## Watchlist

`AAPL` · `MSFT` · `GOOGL` · `AMZN` · `TSLA` · `NVDA`

## Architecture

```
EventBridge (weekday 4:30 PM EST)
        │
        ▼
  Ingestion Lambda ──► Massive API (Grouped Daily)
        │
        ▼
    DynamoDB (stock-movers)
        ▲
        │
    API Lambda ◄── API Gateway (GET /movers)
                          ▲
                          │
                  CloudFront + S3 (React SPA)
```

| Layer       | Technology                     |
|-------------|--------------------------------|
| IaC         | AWS CDK (Python)               |
| Backend     | Python 3.12 (AWS Lambda)       |
| Data Store  | DynamoDB (PAY_PER_REQUEST)     |
| API         | API Gateway (REST)             |
| Frontend    | React + TypeScript (Vite)      |
| Hosting     | CloudFront + S3                |
| Secrets     | SSM Parameter Store            |
| Stock Data  | Massive API (Grouped Daily)    |
| CI/CD       | GitHub Actions                 |

## Project Structure

```
├── backend/
│   ├── lambdas/
│   │   ├── ingestion/handler.py   # Daily cron — fetches stock data, finds top mover
│   │   └── api/handler.py         # GET /movers — returns last 7 days from DynamoDB
│   └── layer/requirements.txt     # Shared Lambda layer dependencies
├── frontend/                      # Vite + React + TypeScript
│   └── src/
│       ├── App.tsx
│       ├── components/MoverTable.tsx
│       ├── hooks/useMovers.ts
│       └── types/index.ts
├── infra/                         # AWS CDK (Python)
│   ├── app.py
│   ├── cdk.json
│   ├── deploy.sh                  # Full infrastructure deployment script
│   ├── requirements.txt
│   └── stacks/
│       ├── pipeline_stack.py      # Composes all constructs
│       └── constructs/
│           ├── database.py        # DynamoDB table
│           ├── ingestion.py       # Lambda + EventBridge + SSM
│           ├── api.py             # Lambda + API Gateway
│           └── frontend.py        # S3 + CloudFront + BucketDeployment
└── .github/workflows/deploy.yml   # CI/CD — updates code on push to main
```

## How It Works

1. **EventBridge** triggers the Ingestion Lambda at 9:30 PM UTC (4:30 PM EST) on weekdays, after market close.
2. **Ingestion Lambda** calls the Massive Grouped Daily endpoint for all US stocks, filters to the watchlist, calculates `((close - open) / open) * 100` for each, and writes the top mover (highest absolute % change) to DynamoDB.
3. **API Lambda** serves `GET /movers` via API Gateway, returning the last 7 days of top movers sorted by date descending.
4. **React SPA** hosted on S3 behind CloudFront fetches from the API and displays the history in a color-coded table (green for gains, red for losses).

## Deployment

### Prerequisites

- AWS CLI configured with a Free Tier account
- AWS CDK CLI (`npm install -g aws-cdk`)
- Node.js >= 20
- Python >= 3.9
- Massive API key ([sign up at massive.com](https://massive.com))

### First-Time Setup

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/stocks-serverless-pipeline.git
cd stocks-serverless-pipeline

# 2. Create .env with your Massive API key
echo "MASSIVE_API_KEY=your_key_here" > .env

# 3. Install CDK dependencies
cd infra
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 4. Bootstrap CDK (one-time per account/region)
cdk bootstrap aws://YOUR_ACCOUNT_ID/us-east-1

# 5. Build the frontend
cd ../frontend
npm install && npm run build

# 6. Deploy the full stack
cd ../infra
./deploy.sh
```

CDK outputs the **CloudFront URL** and **API Gateway URL** on success.

### Subsequent Deploys

For infrastructure changes (new resources, config changes):
```bash
cd infra && ./deploy.sh
```

For code-only changes (Lambda handlers, frontend), push to `main` and GitHub Actions handles it automatically — no full CDK deploy needed.

### GitHub Actions Setup

Add these secrets in **Settings > Secrets and variables > Actions**:

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `MASSIVE_API_KEY`

Every push to `main` updates Lambda code, rebuilds the frontend, syncs to S3, and invalidates the CloudFront cache.

### Manual Testing

```bash
# Invoke the ingestion Lambda
aws lambda invoke --function-name FUNCTION_NAME --region us-east-1 /tmp/out.json && cat /tmp/out.json

# Check DynamoDB
aws dynamodb scan --table-name stock-movers --region us-east-1

# Test the API
curl https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/prod/movers
```

### Tear Down

```bash
cd infra
source .venv/bin/activate
cdk destroy
```

## Separation of Concerns

- **Ingestion Lambda** handles only data collection: API calls, calculation, and DynamoDB writes. Triggered by EventBridge on a cron schedule.
- **API Lambda** handles only data retrieval: reads from DynamoDB and returns JSON. Triggered by API Gateway HTTP requests.
- **CDK constructs** are modular: `database.py`, `ingestion.py`, `api.py`, and `frontend.py` each manage their own resources and can be modified independently.

## Error Handling

- **Rate limiting**: Ingestion Lambda retries up to 3 times with exponential backoff on HTTP 429 responses.
- **Server errors**: Retries on 5xx with backoff.
- **Data not ready**: If the free tier returns 403 for today's date (data available after market close), the Lambda falls back to the previous trading day.
- **Weekends/holidays**: `get_trading_date()` skips back to the most recent weekday.
- **Zero open price**: Stocks with a zero open price are skipped to avoid division-by-zero.
- **API failure**: API Lambda returns a structured 500 JSON response instead of crashing.

## Security

- Massive API key stored in AWS SSM Parameter Store as a SecureString (KMS encrypted at rest).
- `.gitignore` excludes `.env`, `cdk-outputs.json`, and `cdk.out/`.
- Lambda IAM roles follow least privilege: ingestion gets DynamoDB write + SSM read, API gets DynamoDB read only.
- No AWS credentials or API keys in source code.

## Trade-offs

- **Grouped Daily endpoint** — One API call fetches all ~12,000 US stocks instead of 6 individual calls, staying well within the free tier limit of 5 requests/minute.
- **Single CDK stack** — Simpler to deploy and tear down than multi-stack. Modularity comes from separate CDK Construct classes.
- **CloudFront** — Adds HTTPS and edge caching but takes ~5 minutes to deploy. Worth it for production-grade hosting.
- **DynamoDB Scan** — The table holds at most ~260 rows/year (weekdays only). A Scan with limit and in-memory sort is cheaper and simpler than maintaining a GSI.
- **No Lambda Layer** — Both handlers use only stdlib + boto3 (included in Lambda runtime), so no external dependencies are needed at this time.
- **GitHub Actions for CI/CD** — Pushes update Lambda code and frontend directly via AWS CLI rather than running a full CDK deploy, reducing deploy time from ~5 minutes to ~30 seconds.
