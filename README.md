# GarudaBot - Discord Ticket Management Bot

A Discord bot for managing mentorship tickets during hackathons.

Tool guide: [Notion Link](https://www.notion.so/garudahq/Garudabot-Tool-Guide-232229d7e8f88082bd86c7566bd838a5?source=copy_link)

## Cloud Run Deployment

### Prerequisites

1. **Google Cloud CLI** installed and authenticated
2. **Discord Bot Token** from Discord Developer Portal
3. **Firebase Project** with Firestore database
4. **Firebase Service Account** credentials

### Environment Variables

Set these environment variables before deployment:

```bash
export DISCORD_TOKEN="your_discord_bot_token"
export FIREBASE_PROJECT_ID="your_firebase_project_id"
export FIREBASE_CREDENTIALS='{"type":"service_account","project_id":"...","private_key":"...","client_email":"..."}'
```

### Quick Deployment

```bash
# Deploy to Cloud Run
./cloud-run-deploy.sh your-project-id us-central1
```

### Manual Deployment

```bash
# Set your project
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Deploy
gcloud run deploy garudabot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 1 \
  --set-env-vars "DISCORD_TOKEN=$DISCORD_TOKEN,FIREBASE_PROJECT_ID=$FIREBASE_PROJECT_ID,FIREBASE_CREDENTIALS=$FIREBASE_CREDENTIALS"
```

### Post-Deployment Setup

1. **Configure Discord Bot**:
   - Add bot to your Discord server
   - Grant necessary permissions

2. **Set up channels**:
   ```
   !setup
   ```

3. **Post ticket interface**:
   ```
   !post_interface
   ```

### Monitoring

```bash
# View logs
gcloud logs tail --service=garudabot --region=us-central1

# Get service URL
gcloud run services describe garudabot --region=us-central1 --format='value(status.url)'
```

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your credentials

# Run bot
python main.py
```

## Commands

### Hacker Commands
- `!create` - Create a new ticket
- `!list` - List your tickets
- `!info <ticket_id>` - Get ticket information
- `!close_ticket <ticket_id>` - Close your ticket

### Mentor Commands
- `!mentor tickets` - View all open tickets
- `!mentor accept <ticket_id>` - Accept a ticket
- `!mentor resolve <ticket_id>` - Resolve a ticket
- `!mentor assign <ticket_id> <user>` - Assign ticket to another mentor
- `!mentor my` - View your assigned tickets

### Admin Commands
- `!setup` - Configure channels interactively
- `!post` - Post the ticket creation interface (Manual)

## Architecture

- **Discord.py** - Discord bot framework
- **Firebase Firestore** - Database
- **Google Cloud Run** - Hosting platform
- **Docker** - Containerization