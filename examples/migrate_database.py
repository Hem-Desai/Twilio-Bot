#!/usr/bin/env python3
"""
Database Migration Script for Conversation Summarization

This script adds the summary column to existing conversation databases.

Usage:
    python examples/migrate_database.py
"""

import os
import sys
import sqlite3

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def migrate_database():
    """Add summary column to conversations table"""
    database_path = os.path.join(os.getcwd(), 'conversations.db')
    
    if not os.path.exists(database_path):
        print("❌ No existing database found. Run the phone bot first to create one.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(database_path)
        cursor = conn.cursor()
        
        # Check if summary column already exists
        cursor.execute("PRAGMA table_info(conversations)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'summary' in columns:
            print("✅ Summary column already exists in database")
            return True
        
        # Add summary column
        print("📊 Adding summary column to conversations table...")
        cursor.execute("ALTER TABLE conversations ADD COLUMN summary TEXT")
        conn.commit()
        
        print("✅ Database migration completed successfully!")
        print("   - Added 'summary' column to conversations table")
        
        # Show current table structure
        cursor.execute("PRAGMA table_info(conversations)")
        columns = cursor.fetchall()
        print("\n📋 Current table structure:")
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    print("🔄 Database Migration for Conversation Summarization")
    print("=" * 55)
    
    if migrate_database():
        print("\n🎉 Migration completed! You can now:")
        print("1. Use the conversation summarization features")
        print("2. Run: python examples/test_summarization.py")
        print("3. View summaries in the dashboard")
    else:
        print("\n💡 If you're starting fresh, just run the phone bot:")
        print("   python examples/groq_phone_bot.py")
        print("   The new database will automatically include the summary column.")

if __name__ == "__main__":
    main() 