# Deployment Scenarios - Change Detection Examples

## Scenario 1: Change to Audio Transcriber Service Only

**Changed File:** `services/audio-transcriber/src/main.py`

**What Happens:**
- ✅ `deploy-audio-transcriber.yml` workflow triggers
- ❌ `deploy-file-watcher.yml` workflow does NOT trigger
- ❌ `deploy-conversation-parser.yml` workflow does NOT trigger
- ❌ `deploy-questionnaire-processor.yml` workflow does NOT trigger

**Result:** Only the Audio Transcriber service is rebuilt and redeployed.

---

## Scenario 2: Change to Shared Utils Package

**Changed File:** `shared/utils/src/aws.py` (the file you have open)

**What Happens:**
- ✅ `deploy-file-watcher.yml` workflow triggers (uses shared/utils)
- ✅ `deploy-audio-transcriber.yml` workflow triggers (uses shared/utils)
- ✅ `deploy-conversation-parser.yml` workflow triggers (uses shared/utils)
- ✅ `deploy-questionnaire-processor.yml` workflow triggers (uses shared/utils)

**Result:** All services that depend on shared packages are rebuilt and redeployed.

---

## Scenario 3: Change to Database Models

**Changed File:** `shared/models/src/conversation.py`

**What Happens:**
- ✅ All service workflows trigger (all use shared/models)

**Result:** All services are rebuilt to include the updated models.

---

## Scenario 4: Change to Infrastructure Only

**Changed File:** `aws/infrastructure/infrastructure_stack.py`

**What Happens:**
- ✅ `deploy-infrastructure.yml` workflow triggers
- ❌ No service workflows trigger

**Result:** Only infrastructure is updated via CDK, no services are rebuilt.

---

## Scenario 5: Multiple Service Changes

**Changed Files:** 
- `services/file-watcher/src/handler.py`
- `services/conversation-parser/src/main.py`

**What Happens:**
- ✅ `deploy-file-watcher.yml` workflow triggers
- ❌ `deploy-audio-transcriber.yml` workflow does NOT trigger
- ✅ `deploy-conversation-parser.yml` workflow triggers
- ❌ `deploy-questionnaire-processor.yml` workflow does NOT trigger

**Result:** Only File Watcher and Conversation Parser are redeployed.

---

## How GitHub Actions Processes This

1. **Git Push Event**: When you push to `main` or `develop`
2. **Path Filter Check**: GitHub checks which files changed in the commit
3. **Workflow Triggering**: Only workflows whose path filters match run
4. **Parallel Execution**: Multiple workflows can run in parallel

## Example Git Commands

```bash
# Change only audio-transcriber
git add services/audio-transcriber/src/main.py
git commit -m "AudioTranscriber: fix transcription timeout"
git push origin develop
# Result: Only audio-transcriber deploys to DEV

# Change shared utils
git add shared/utils/src/aws.py
git commit -m "SQSClient: add retry logic"
git push origin develop
# Result: All services deploy to DEV (all use shared utils)

# Change multiple services
git add services/file-watcher/src/handler.py
git add services/conversation-parser/src/main.py
git commit -m "Multiple: update error handling"
git push origin develop
# Result: Only file-watcher and conversation-parser deploy
```

## Branch-Based Environment Selection

- **Push to `develop`**: Deploys to DEV environment
- **Push to `main`**: Deploys to PROD environment

```yaml
environment: ${{ github.ref == 'refs/heads/main' && 'PROD' || 'DEV' }}
```

## Manual Override

Each workflow also has `workflow_dispatch` for manual deployment:

```yaml
workflow_dispatch:
  inputs:
    environment:
      description: 'Environment to deploy to'
      required: true
      default: 'DEV'
      type: choice
      options:
        - DEV
        - PROD
```

This allows you to manually trigger deployment of any service to any environment from GitHub Actions UI.