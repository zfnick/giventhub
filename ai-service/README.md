# GITEventHub AI Service

Python service workspace for the Google ADK-powered GITEventHub orchestrator.

## Setup

This venv was created with the Homebrew Python interpreter:

```sh
/opt/homebrew/opt/python@3.14/bin/python3.14 -m venv .venv
```

Activate it from this folder:

```sh
source .venv/bin/activate
```

Installed package:

```sh
python -m pip install -r requirements.txt
```

## Local Configuration

Copy the example environment file and fill in your Google Cloud project:

```sh
cp .env.example .env
```

For Google Cloud credits, use Vertex AI / Gemini Enterprise Agent Platform:

```sh
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=global
```

Authenticate locally:

```sh
gcloud auth application-default login
gcloud config set project your-project-id
```

## Run

```sh
source .venv/bin/activate
adk run git_eventhub_agent
```

Try:

```text
Find promising climate-tech startups that Cradle should reconnect with and draft outreach.
```
