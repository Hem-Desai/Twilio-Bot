#!/usr/bin/env python3
"""
Test script for conversation summarization using Groq

This script demonstrates how to generate AI-powered summaries 
of existing conversations in the database.

Usage:
    python examples/test_summarization.py
"""

import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_convo.database import DatabaseManager
from llm_convo.conversation_summarizer import create_summary_service
from llm_convo.env_utils import load_env_file, check_groq_setup

def main():
    print("🤖 Conversation Summarization Test with Groq")
    print("=" * 50)
    
    # Load environment
    try:
        load_env_file()
        if not check_groq_setup():
            return
    except Exception as e:
        print(f"⚠️ Environment setup issue: {e}")
        return
    
    # Initialize database
    database_url = f"sqlite:///{os.path.join(os.getcwd(), 'conversations.db')}"
    print(f"📊 Using database: {database_url}")
    
    try:
        # Create summary service
        summary_service = create_summary_service(database_url)
        db_manager = DatabaseManager(database_url)
        
        # Get all conversations
        conversations = db_manager.get_all_conversations(limit=10)
        
        if not conversations:
            print("❌ No conversations found in database")
            print("\n💡 Run the phone bot first to create some conversations:")
            print("   python examples/groq_phone_bot.py")
            return
        
        print(f"📋 Found {len(conversations)} conversations")
        print()
        
        # Show conversation list
        for i, conv in enumerate(conversations, 1):
            status_emoji = "✅" if conv.status == 'completed' else "⏳" if conv.status == 'active' else "❌"
            summary_status = "📝" if conv.summary else "❌"
            
            print(f"{i}. {status_emoji} Call {conv.call_sid[:8]}... "
                  f"({conv.status}) - {len(conv.messages)} messages - "
                  f"Summary: {summary_status}")
        
        print()
        
        # Test options
        while True:
            print("🎯 Choose an action:")
            print("1. Generate summary for a specific conversation")
            print("2. Batch generate summaries for all completed conversations")
            print("3. View existing summary")
            print("4. Exit")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == "1":
                conv_num = input(f"Enter conversation number (1-{len(conversations)}): ").strip()
                try:
                    conv_index = int(conv_num) - 1
                    if 0 <= conv_index < len(conversations):
                        conv = conversations[conv_index]
                        print(f"\n🤖 Generating summary for conversation {conv.id}...")
                        
                        summary = summary_service.generate_and_save_summary(conv.id)
                        if summary:
                            print("✅ Summary generated successfully!")
                            print("\n📝 Summary:")
                            print("-" * 40)
                            print(summary)
                            print("-" * 40)
                        else:
                            print("❌ Failed to generate summary")
                    else:
                        print("❌ Invalid conversation number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "2":
                print("\n🤖 Generating summaries for all completed conversations...")
                stats = summary_service.batch_generate_summaries(limit=50)
                print(f"\n📊 Batch Summary Results:")
                print(f"   Processed: {stats['processed']}")
                print(f"   Successful: {stats['successful']}")
                print(f"   Failed: {stats['failed']}")
                print(f"   Skipped: {stats['skipped']}")
            
            elif choice == "3":
                conv_num = input(f"Enter conversation number (1-{len(conversations)}): ").strip()
                try:
                    conv_index = int(conv_num) - 1
                    if 0 <= conv_index < len(conversations):
                        conv = conversations[conv_index]
                        summary = summary_service.get_summary(conv.id)
                        if summary:
                            print("\n📝 Existing Summary:")
                            print("-" * 40)
                            print(summary)
                            print("-" * 40)
                        else:
                            print("❌ No summary available for this conversation")
                    else:
                        print("❌ Invalid conversation number")
                except ValueError:
                    print("❌ Please enter a valid number")
            
            elif choice == "4":
                print("👋 Goodbye!")
                break
            
            else:
                print("❌ Invalid choice. Please enter 1-4.")
            
            print()
        
        # Close database
        db_manager.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("1. Set up your GROQ_API_KEY in .env file")
        print("2. Run the phone bot to create conversations")
        print("3. Installed all dependencies: pip install -r requirements.txt")


if __name__ == "__main__":
    main() 