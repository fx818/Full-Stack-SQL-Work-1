#!/usr/bin/env python3
"""
Supabase Connection Diagnostic Script
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_supabase_connection():
    """Test Supabase connection with detailed diagnostics"""
    
    # Get configuration
    host = os.getenv("SUPABASE_HOST", "db.fzrbnsljevwhexjnfqtz.supabase.co")
    port = int(os.getenv("SUPABASE_PORT", "5432"))
    database = os.getenv("SUPABASE_DATABASE", "postgres")
    user = os.getenv("SUPABASE_USER", "postgres")
    password = os.getenv("SUPABASE_PASSWORD", "")
    
    print("=== Supabase Connection Diagnostics ===")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    print(f"Password: {'[SET]' if password else '[NOT SET]'}")
    print()
    
    if not password:
        print("❌ ERROR: SUPABASE_PASSWORD is not set!")
        print("Please set the SUPABASE_PASSWORD environment variable.")
        return False
    
    print("Attempting connection...")
    
    try:
        # Test basic connection
        connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            cursor_factory=RealDictCursor,
            connect_timeout=10  # 10-second timeout
        )
        
        print("✅ Connection successful!")
        
        # Test query execution
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            result = cursor.fetchone()
            if result:
                version = result[0] if isinstance(result, (list, tuple)) else str(result)
                print(f"✅ Query test successful!")
                print(f"Database version: {version}")
            else:
                print("⚠️ Query returned no results")
        
        # Test table creation permission
        with connection.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_connection_check (
                    id SERIAL PRIMARY KEY,
                    test_data VARCHAR(50)
                );
            """)
            print("✅ Table creation test successful!")
            
            # Clean up test table
            cursor.execute("DROP TABLE IF EXISTS test_connection_check;")
        
        connection.close()
        print("\n✅ All tests passed! Supabase connection is working properly.")
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Connection failed: {e}")
        
        error_str = str(e).lower()
        if "password authentication failed" in error_str:
            print("\n💡 Troubleshooting suggestions:")
            print("• Check that your SUPABASE_PASSWORD is correct")
            print("• Verify your Supabase project credentials")
        elif "timeout" in error_str or "could not connect" in error_str:
            print("\n💡 Troubleshooting suggestions:")
            print("• Check your internet connection")
            print("• Verify the SUPABASE_HOST is correct")
            print("• Check if your firewall is blocking connections")
        elif "database" in error_str and "does not exist" in error_str:
            print("\n💡 Troubleshooting suggestions:")
            print("• Check that your database name is correct")
            print("• Verify your Supabase project is active")
        else:
            print(f"\n💡 General troubleshooting:")
            print("• Double-check all Supabase credentials")
            print("• Ensure your Supabase project is not paused")
            print("• Check Supabase project settings")
        
        return False
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    test_supabase_connection() 