# Stocks Serverless Pipeline

A fully automated serverless system that identifies the top-moving stock each day from a tech watchlist, stores the results in DynamoDB, and displays the history on a public website.

## Watchlist

`AAPL` · `MSFT` · `GOOGL` · `AMZN` · `TSLA` · `NVDA`

## Architecture

```
EventBridge (daily cron)
        │
        ▼
  Ingestion Lambda ──► Massive API
        │
        ▼
    DynamoDB
        ▲
        │
    API Lambda ◄── API Gateway (GET /movers)
                          ▲
                          │
                  CloudFront + S3 (React SPA)
```

## Tech Stack

| Layer          | Technology                        |
|----------------|-----------------------------------|
| IaC            | AWS CDK (Python)                  |
| Backend        | Python (AWS Lambda)               |
| Data Store     | DynamoDB                          |
| API            | API Gateway (REST)                |
| Frontend       | React + TypeScript + Tailwind CSS |
| Hosting        | CloudFront + S3                   |
| Secrets        | SSM Parameter Store               |
| Stock Data     | Massive API                       |

## Project Structure

```
├── backend/
│   ├── lambdas/
│   │   ├── ingestion/        # Daily cron — fetches stock data, finds top mover
│   │   │   └── handler.py
│   │   └── api/              # GET /movers — returns last 7 days from DynamoDB
│   │       └── handler.py
│   └── layer/                # Shared Python dependencies (Lambda Layer)
│       └── requirements.txt
├── frontend/                 # Vite + React + TypeScript + Tailwind
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── types/
│   └── public/
├── infra/                    # AWS CDK (Python)
│   ├── app.py
│   ├── cdk.json
│   ├── requirements.txt
│   └── stacks/
│       ├── pipeline_stack.py
│       └── constructs/
│           ├── database.py
│           ├── ingestion.py
│           ├── api.py
│           └── frontend.py
└── README.md
```

## How It Works

1. **EventBridge** triggers the Ingestion Lambda at 4:30 PM ET on weekdays (after market close).
2. **Ingestion Lambda** calls the Massive Grouped Daily endpoint for all US stocks, filters to the watchlist, calculates `((close - open) / open) * 100` for each, and writes the top mover to DynamoDB.
3. **API Lambda** serves `GET /movers` via API Gateway, returning the last 7 days of top movers from DynamoDB.
4. **React SPA** hosted on S3 behind CloudFront fetches from the API and displays the history in a color-coded table (green = gain, red = loss).

## Deployment

### Prerequisites

- AWS CLI configured with Free Tier account
- AWS CDK CLI (`npm install -g aws-cdk`)
- Node.js >= 18
- Python >= 3.11
- Massive API key ([sign up at massive.com](https://massive.com))

### Quick Start

```bash
# 1. Install CDK dependencies
cd infra
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Build frontend
cd ../frontend
npm install && npm run build

# 3. Bootstrap CDK (first time only)
cd ../infra
cdk bootstrap

# 4. Deploy the stack
cdk deploy --context massive_api_key=YOUR_KEY_HERE
```

CDK outputs the CloudFront URL and API Gateway URL on success.

### Tear Down

```bash
cd infra
cdk destroy
```

## Security

- The Massive API key is stored in AWS SSM Parameter Store as a SecureString — never committed to source.
- `.gitignore` excludes `.env`, `cdk.context.json`, and `cdk.out/`.

## Trade-offs

- **Grouped Daily endpoint** — One API call fetches all US stocks instead of 6 individual calls, staying well within the free tier limit of 5 requests/minute.
- **Single CDK stack** — Simpler to deploy and tear down than multi-stack. Modularity comes from separate CDK Construct classes.
- **CloudFront** — Adds HTTPS and edge caching but takes ~5 minutes to deploy/invalidate. Worth it for production-grade hosting.
- **DynamoDB Scan** — The table holds at most ~260 rows/year (weekdays only). A Scan with limit 7 is cheaper and simpler than maintaining a GSI.
