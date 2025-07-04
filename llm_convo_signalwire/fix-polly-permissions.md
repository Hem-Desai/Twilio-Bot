# Fix Amazon Polly Permissions Issue

## Problem

Your AWS user `hem-desai` doesn't have permission to use Amazon Polly's `SynthesizeSpeech` operation.

## Solutions

### Option 1: AWS Console (Easiest)

1. **Login to AWS Console**: https://console.aws.amazon.com/iam/
2. **Go to IAM** → **Users** → **hem-desai**
3. **Click "Add permissions"** → **"Attach existing policies directly"**
4. **Search and attach**: `AmazonPollyReadOnlyAccess`
   - This gives you SynthesizeSpeech + other read operations
5. **Save changes**

### Option 2: AWS CLI Commands

```bash
# Create the policy
aws iam create-policy \
    --policy-name PollyBasicAccess \
    --policy-document file://aws-polly-policy.json

# Attach policy to user (replace ACCOUNT-ID with your AWS account ID)
aws iam attach-user-policy \
    --user-name hem-desai \
    --policy-arn arn:aws:iam::ACCOUNT-ID:policy/PollyBasicAccess
```

### Option 3: Use AWS Managed Policy

```bash
# Attach AWS managed policy (simpler)
aws iam attach-user-policy \
    --user-name hem-desai \
    --policy-arn arn:aws:iam::aws:policy/AmazonPollyReadOnlyAccess
```

## Test After Changes

Run the test again to verify it works:

```bash
cd llm_convo_signalwire
python start.py --test-services
```

## Expected Result

After fixing permissions, you should see:

```
✅ Amazon Polly    PASS
```

## Alternative: Use Different TTS Service

If AWS permissions are complex, you can switch to:

- **Google Cloud Text-to-Speech**
- **ElevenLabs**
- **Azure Cognitive Services**

Update the `TTS_SERVICE` in your `.env` file to use alternatives.
