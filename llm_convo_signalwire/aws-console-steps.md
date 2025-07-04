# 🎯 AWS Console Step-by-Step Guide for Polly Permissions

## Current Situation

- User: hem-desai has **0 permissions policies**
- **Permissions boundary is set** (this is restricting actions)
- Need to add Polly permissions

## Method 1: Attach AWS Managed Policy (Easiest)

### Step 1: Click "Add permissions"

- In the top-right corner, click the blue **"Add permissions"** button
- From the dropdown, select **"Attach policies directly"**

### Step 2: Search for Polly Policy

- In the search box, type: `AmazonPollyFullAccess`
- Check the box next to **"AmazonPollyFullAccess"**
- Click **"Next"** → **"Add permissions"**

## Method 2: Create Custom Inline Policy (More Secure)

### Step 1: Create Inline Policy

- Click **"Add permissions"** → **"Create inline policy"**

### Step 2: Use JSON Editor

- Click the **"JSON"** tab
- Replace the default content with:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowPollyOperations",
      "Effect": "Allow",
      "Action": [
        "polly:SynthesizeSpeech",
        "polly:DescribeVoices",
        "polly:GetLexicon",
        "polly:ListLexicons"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 3: Save Policy

- Click **"Review policy"**
- Name it: `PollyAccess`
- Click **"Create policy"**

## ⚠️ Important Notes

### About Permissions Boundary

The "Permissions boundary (set)" you see might be limiting what policies can be attached. If you get errors:

1. **Contact your AWS administrator** - they may need to modify the permissions boundary
2. **Try Method 1 first** - managed policies are sometimes allowed when custom policies aren't
3. **The boundary might allow Polly** - even if it blocks other services

### Testing After Changes

After adding permissions:

1. **Wait 2-3 minutes** for AWS to propagate changes
2. **Test with AWS CLI**:
   ```bash
   aws polly describe-voices --region us-east-1
   ```
3. **Test the application**:
   ```bash
   cd llm_convo_signalwire
   python start.py --test-services
   ```

## Expected Result

After successful permission addition, you should see:

- ✅ **Amazon Polly: PASS** in the service test
- The application can generate speech successfully

## If You Still Get Errors

The permissions boundary might be too restrictive. In that case:

1. Contact the AWS account administrator
2. Ask them to either:
   - Add Polly permissions to the boundary
   - Or attach Polly permissions directly to your user
   - Or provide you with a different AWS user for this project
