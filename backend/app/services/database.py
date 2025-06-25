import psycopg2
from psycopg2.extras import RealDictCursor, RealDictRow
import json
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from core.config import settings

class SupabaseService:
    def __init__(self):
        self.connection: Optional[psycopg2.extensions.connection] = None
        self.connect()
        if self.connection:
            self.create_tables()

    def connect(self):
        """Establish connection to Supabase PostgreSQL"""
        try:
            # Check if password is set
            if not settings.SUPABASE_PASSWORD:
                print("Warning: SUPABASE_PASSWORD is not set in environment variables")
                return
                
            self.connection = psycopg2.connect(
                host=settings.SUPABASE_HOST,
                port=settings.SUPABASE_PORT,
                database=settings.SUPABASE_DATABASE,
                user=settings.SUPABASE_USER,
                password=settings.SUPABASE_PASSWORD,
                cursor_factory=RealDictCursor
            )
            self.connection.autocommit = True
            print("Successfully connected to Supabase!")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            self.connection = None

    def create_tables(self):
        """Create necessary tables for conversation memory"""
        if not self.connection:
            print("No database connection available for table creation")
            return
            
        try:
            with self.connection.cursor() as cursor:
                # Create conversation_memory table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversation_memory_HITL (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) NOT NULL UNIQUE,
                        conversation_history JSONB DEFAULT '[]'::jsonb,
                        question_patterns JSONB DEFAULT '{}'::jsonb,
                        entity_memory JSONB DEFAULT '{}'::jsonb,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Create index on username for faster queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_conversation_memory_username 
                    ON conversation_memory_HITL(username);
                """)
                
                # Create update trigger
                cursor.execute("""
                    CREATE OR REPLACE FUNCTION update_updated_at_column()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ language 'plpgsql';
                """)
                
                cursor.execute("""
                    DROP TRIGGER IF EXISTS update_conversation_memory_updated_at ON conversation_memory_HITL;
                    CREATE TRIGGER update_conversation_memory_updated_at
                        BEFORE UPDATE ON conversation_memory_HITL
                        FOR EACH ROW
                        EXECUTE FUNCTION update_updated_at_column();
                """)
                
                print("Tables created successfully!")
                
        except Exception as e:
            print(f"Error creating tables: {e}")

    def get_user_memory(self, username: str) -> Optional[Dict[str, Any]]:
        """Get conversation memory for a specific user"""
        if not self.connection:
            print("No database connection available")
            return None
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT conversation_history, question_patterns, entity_memory, created_at, updated_at
                    FROM conversation_memory_HITL
                    WHERE username = %s
                """, (username,))
                
                result = cursor.fetchone()
                if result:
                    # Use getattr or dict access with fallback for RealDictRow
                    return {
                        'username': username,
                        'conversation_history': dict(result)['conversation_history'],
                        'question_patterns': dict(result)['question_patterns'],  
                        'entity_memory': dict(result)['entity_memory'],
                        'created_at': dict(result)['created_at'],
                        'updated_at': dict(result)['updated_at']
                    }
                return None
        except Exception as e:
            print(f"Error getting user memory: {e}")
            return None

    def save_user_memory(self, username: str, conversation_history: List[Dict], 
                        question_patterns: Dict, entity_memory: Dict) -> bool:
        """Save or update conversation memory for a user"""
        if not self.connection:
            print("No database connection available")
            return False
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO conversation_memory_HITL (username, conversation_history, question_patterns, entity_memory)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (username) 
                    DO UPDATE SET 
                        conversation_history = EXCLUDED.conversation_history,
                        question_patterns = EXCLUDED.question_patterns,
                        entity_memory = EXCLUDED.entity_memory,
                        updated_at = CURRENT_TIMESTAMP
                """, (username, json.dumps(conversation_history), 
                     json.dumps(question_patterns), json.dumps(entity_memory)))
                
                return True
        except Exception as e:
            print(f"Error saving user memory: {e}")
            return False

    def clear_user_memory(self, username: str) -> bool:
        """Clear conversation memory for a user"""
        if not self.connection:
            print("No database connection available")
            return False
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE conversation_memory_HITL
                    SET conversation_history = '[]'::jsonb,
                        question_patterns = '{}'::jsonb,
                        entity_memory = '{}'::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE username = %s
                """, (username,))
                
                return True
        except Exception as e:
            print(f"Error clearing user memory: {e}")
            return False

    def delete_user_memory(self, username: str) -> bool:
        """Delete all memory for a user"""
        if not self.connection:
            print("No database connection available")
            return False
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("DELETE FROM conversation_memory_HITL WHERE username = %s", (username,))
                return True
        except Exception as e:
            print(f"Error deleting user memory: {e}")
            return False

    def get_all_users(self) -> List[str]:
        """Get list of all users with memory"""
        if not self.connection:
            print("No database connection available")
            return []
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT username FROM conversation_memory_HITL ORDER BY updated_at DESC")
                results = cursor.fetchall()
                return [str(dict(row)['username']) for row in results]  # Convert to dict for key access
        except Exception as e:
            print(f"Error getting all users: {e}")
            return []

    def health_check(self) -> bool:
        """Check if database connection is healthy"""
        if not self.connection:
            print("Database health check failed: No connection")
            return False
            
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                print("Database health check passed")   
                return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            self.connection = None

# Global database instance
db_service = SupabaseService()