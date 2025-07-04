# 🔧 AWS Polly Setup Guide

## Problem

Your AWS user `hem-desai` lacks IAM permissions for Amazon Polly operations.

## Solution Options

### Option 1: Fix Existing User (Recommended)

1. **AWS Console Method**:
   - Login to [AWS IAM Console](https://console.aws.amazon.com/iam/) with admin credentials
   - Navigate to Users → `hem-desai`
   - Click "Add permissions" → "Attach policies directly"
   - Create new policy with this JSON:

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

2. **AWS CLI Method** (if you have admin user):

```bash
aws iam put-user-policy --user-name hem-desai --policy-name PollyAccess --policy-document file://aws-polly-policy.json
```

### Option 2: Create New AWS User

1. **Create User**:

```bash
aws iam create-user --user-name llm-convo-polly
aws iam create-access-key --user-name llm-convo-polly
```

2. **Attach Policy**:

```bash
aws iam attach-user-policy --user-name llm-convo-polly --policy-arn arn:aws:iam::aws:policy/AmazonPollyFullAccess
```

### Option 3: Use AWS Managed Policy

Attach the managed policy:

- `AmazonPollyFullAccess` (full access)
- `AmazonPollyReadOnlyAccess` + custom synthesis policy

## Testing After Fix

Test with AWS CLI:

```bash
aws polly describe-voices --region us-east-1
aws polly synthesize-speech --text "Hello World" --voice-id Joanna --output-format mp3 test.mp3
```

Test with application:

```bash
python start.py --test-services
```

## Security Best Practices

1. **Least Privilege**: Only grant necessary Polly permissions
2. **Region Restriction**: Limit to specific AWS regions if needed
3. **Resource Restriction**: Limit to specific resources if required

## Common Issues

- **Permissions Boundary**: Your user may have a permissions boundary limiting actions
- **Multi-Factor Authentication**: Some operations may require MFA
- **Region Mismatch**: Ensure you're using the correct AWS region

## Next Steps

After applying permissions:

1. Wait 2-3 minutes for AWS to propagate changes
2. Test with `aws polly describe-voices`
3. Run `python start.py --test-services`
4. If successful, the Polly test should show ✅ PASS
