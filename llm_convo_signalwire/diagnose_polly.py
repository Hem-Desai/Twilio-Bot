#!/usr/bin/env python3
"""
Amazon Polly Diagnostic Script
Helps diagnose and troubleshoot Polly permission issues.
"""

import boto3
import json
import os
import sys
from botocore.exceptions import ClientError, NoCredentialsError
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent))
from config.settings import settings

def print_banner():
    """Print diagnostic banner"""
    print("=" * 60)
    print("🔧 AMAZON POLLY DIAGNOSTIC TOOL")
    print("=" * 60)
    print()

def check_aws_credentials():
    """Check if AWS credentials are configured"""
    print("🔍 Checking AWS Credentials...")
    
    try:
        # Check environment variables
        aws_key = settings.AWS_ACCESS_KEY_ID
        aws_secret = settings.AWS_SECRET_ACCESS_KEY
        aws_region = settings.AWS_REGION
        
        if not aws_key or not aws_secret:
            print("❌ AWS credentials not found in environment variables")
            return False
        
        # Mask credentials for display
        masked_key = aws_key[:8] + "*" * (len(aws_key) - 12) + aws_key[-4:] if len(aws_key) > 12 else aws_key[:4] + "*" * 4
        
        print(f"✅ AWS Access Key: {masked_key}")
        print(f"✅ AWS Region: {aws_region}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking credentials: {e}")
        return False

def check_aws_identity():
    """Check AWS identity using STS"""
    print("\n🔍 Checking AWS Identity...")
    
    try:
        client = boto3.client(
            'sts',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        response = client.get_caller_identity()
        
        print(f"✅ User ARN: {response['Arn']}")
        print(f"✅ Account ID: {response['Account']}")
        print(f"✅ User ID: {response['UserId']}")
        
        return True
        
    except ClientError as e:
        print(f"❌ AWS STS Error: {e}")
        return False
    except NoCredentialsError:
        print("❌ No AWS credentials found")
        return False
    except Exception as e:
        print(f"❌ Error checking identity: {e}")
        return False

def test_polly_permissions():
    """Test various Polly operations"""
    print("\n🔍 Testing Polly Permissions...")
    
    try:
        client = boto3.client(
            'polly',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        
        # Test DescribeVoices
        print("  Testing polly:DescribeVoices...")
        try:
            response = client.describe_voices()
            voices_count = len(response.get('Voices', []))
            print(f"  ✅ DescribeVoices successful ({voices_count} voices found)")
        except ClientError as e:
            print(f"  ❌ DescribeVoices failed: {e}")
        
        # Test SynthesizeSpeech
        print("  Testing polly:SynthesizeSpeech...")
        try:
            response = client.synthesize_speech(
                Text="This is a test",
                OutputFormat='mp3',
                VoiceId='Joanna',
                Engine='neural'
            )
            
            if 'AudioStream' in response:
                audio_data = response['AudioStream'].read()
                print(f"  ✅ SynthesizeSpeech successful ({len(audio_data)} bytes)")
                return True
            else:
                print("  ❌ SynthesizeSpeech failed: No audio stream")
                return False
                
        except ClientError as e:
            print(f"  ❌ SynthesizeSpeech failed: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Error testing Polly: {e}")
        return False

def suggest_fixes():
    """Suggest potential fixes"""
    print("\n🔧 SUGGESTED FIXES:")
    print("=" * 40)
    
    print("\n1. 🏛️ AWS Console Method (Recommended):")
    print("   - Go to https://console.aws.amazon.com/iam/")
    print("   - Navigate to Users → hem-desai")
    print("   - Add permissions → Attach policies directly")
    print("   - Create policy with Polly permissions")
    
    print("\n2. 📋 Required IAM Policy JSON:")
    policy = {
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
    print(json.dumps(policy, indent=2))
    
    print("\n3. 🖥️ AWS CLI Method (if you have admin access):")
    print("   aws iam put-user-policy --user-name hem-desai \\")
    print("     --policy-name PollyAccess \\")
    print("     --policy-document file://aws-polly-policy.json")
    
    print("\n4. 🔄 Alternative: Use AWS Managed Policy:")
    print("   - Attach policy: AmazonPollyFullAccess")
    print("   - Or: AmazonPollyReadOnlyAccess + custom synthesis policy")

def test_application_polly():
    """Test Polly through the application"""
    print("\n🔍 Testing Application Polly Client...")
    
    try:
        from services.polly_client import polly_client
        
        # Run the application test
        import asyncio
        
        async def run_test():
            result = await polly_client.test_synthesis()
            if result:
                print("✅ Application Polly test successful")
                return True
            else:
                print("❌ Application Polly test failed")
                return False
        
        return asyncio.run(run_test())
        
    except Exception as e:
        print(f"❌ Error testing application Polly: {e}")
        return False

def main():
    """Main diagnostic function"""
    print_banner()
    
    # Run diagnostics
    checks_passed = 0
    total_checks = 4
    
    if check_aws_credentials():
        checks_passed += 1
    
    if check_aws_identity():
        checks_passed += 1
    
    if test_polly_permissions():
        checks_passed += 1
    
    if test_application_polly():
        checks_passed += 1
    
    # Print results
    print("\n" + "=" * 60)
    print("📊 DIAGNOSTIC RESULTS")
    print("=" * 60)
    print(f"✅ Checks Passed: {checks_passed}/{total_checks}")
    
    if checks_passed == total_checks:
        print("🎉 All tests passed! Polly should be working correctly.")
    else:
        print("⚠️ Some tests failed. See suggested fixes below.")
        suggest_fixes()
    
    print("\n💡 Next Steps:")
    print("1. Apply the suggested IAM policy fixes")
    print("2. Wait 2-3 minutes for AWS to propagate changes")
    print("3. Run this script again to verify the fix")
    print("4. Test with: python start.py --test-services")

if __name__ == "__main__":
    main() 