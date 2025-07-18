#!/bin/bash

# Deploy Discord Bot to Google Cloud Run
# Usage: ./cloud-run-deploy.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID=${1:-"your-project-id"}
REGION=${2:-"us-central1"}
SERVICE_NAME="garudabot"

echo "🚀 Deploying Discord Bot to Cloud Run..."
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud CLI not found. Please install it first:"
    echo "   brew install google-cloud-sdk"
    exit 1
fi

# Check if required environment variables are set
if [ -z "$DISCORD_TOKEN" ]; then
    echo "❌ DISCORD_TOKEN environment variable is required"
    echo "   export DISCORD_TOKEN=your_discord_token_here"
    exit 1
fi

if [ -z "$FIREBASE_PROJECT_ID" ]; then
    echo "❌ FIREBASE_PROJECT_ID environment variable is required"
    echo "   export FIREBASE_PROJECT_ID=your_firebase_project_id"
    exit 1
fi

if [ -z "$FIREBASE_CREDENTIALS" ]; then
    echo "❌ FIREBASE_CREDENTIALS environment variable is required"
    echo "   export FIREBASE_CREDENTIALS='{\"type\":\"service_account\",...}'"
    exit 1
fi

# Set project
echo "📋 Setting project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Build and deploy
echo "🏗️  Building and deploying..."
gcloud run deploy $SERVICE_NAME \
  --source . \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 1 \
  --set-env-vars "DISCORD_TOKEN=$DISCORD_TOKEN,FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID,FIREBASE_CREDENTIALS=$FIREBASE_CREDENTIALS"

echo "✅ Deployment complete!"
echo ""
echo "📊 View logs:"
echo "   gcloud logs tail --service=$SERVICE_NAME --region=$REGION"
echo ""
echo "🌐 Service URL:"
echo "   gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)'" 