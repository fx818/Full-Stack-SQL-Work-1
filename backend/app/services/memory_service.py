from typing import List, Dict, Any, Optional
from datetime import datetime
import ast
from services.database import db_service

class ConversationMemory:
    def __init__(self, username: str, max_history: int = 10):
        print(f"Initializing memory for {username}")
        self.username = username
        self.max_history = max_history
        self.conversation_history = []
        self.question_patterns = {}
        self.entity_memory = {}
        print(f"Loading from database")
        self.load_from_database()
        print(f"Memory loaded")
    
    def load_from_database(self):
        """Load memory from Supabase database"""
        try:
            memory_data = db_service.get_user_memory(self.username)
            if memory_data:
                self.conversation_history = memory_data.get("conversation_history", [])
                self.question_patterns = memory_data.get("question_patterns", {})
                self.entity_memory = memory_data.get("entity_memory", {})
            else:
                # Initialize empty memory for new user
                self.conversation_history = []
                self.question_patterns = {}
                self.entity_memory = {}
        except Exception as e:
            print(f"Error loading memory for {self.username}: {e}")
            self.conversation_history = []
            self.question_patterns = {}
            self.entity_memory = {}
    
    def save_to_database(self):
        """Save memory to Supabase database"""
        try:
            print(f"Saving to database")
            return db_service.save_user_memory(
                self.username,
                self.conversation_history,
                self.question_patterns,
                self.entity_memory
            )
        except Exception as e:
            print(f"Error saving memory for {self.username}: {e}")
            return False
    
    def add_interaction(self, question: str, query: str, result: str, answer: str):
        """Add a new interaction to memory"""
        interaction = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "query": query,
            "result": result,
            "answer": answer
        }
        
        self.conversation_history.append(interaction)
        
        # Keep only the most recent interactions
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]
        
        # Extract and store question patterns and entities
        self._extract_question_patterns(question, query)
        self._extract_entities(question, result, answer)
        
        # Save to database
        self.save_to_database()
    
    def _extract_entities(self, question: str, result: str, answer: str):
        """Extract and store entities (names, values) from interactions"""
        try:
            if result.startswith('[') and result.endswith(']'):
                parsed_result = ast.literal_eval(result)
                if parsed_result and isinstance(parsed_result, list):
                    for item in parsed_result:
                        if isinstance(item, tuple) and len(item) > 0:
                            entity = str(item[0]).lower()
                            self.entity_memory[entity] = {
                                'question': question,
                                'full_result': result,
                                'answer': answer,
                                'timestamp': datetime.now().isoformat()
                            }
        except:
            pass
    
    def _extract_question_patterns(self, question: str, query: str):
        """Extract patterns from questions for future reference"""
        question_lower = question.lower()
        
        if "student" in question_lower:
            self.question_patterns["student_queries"] = self.question_patterns.get("student_queries", [])
            self.question_patterns["student_queries"].append({"question": question, "query": query})
        
        common_columns = ["name", "marks", "class", "section", "grade", "email", "id"]
        for col in common_columns:
            if col in question_lower:
                pattern_key = f"{col}_queries"
                self.question_patterns[pattern_key] = self.question_patterns.get(pattern_key, [])
                self.question_patterns[pattern_key].append({"question": question, "query": query})
    
    def resolve_contextual_references(self, question: str) -> str:
        """Resolve pronouns and contextual references in the question"""
        question_lower = question.lower()
        resolved_question = question
        
        pronouns = ['her', 'his', 'their', 'it', 'she', 'he', 'they']
        
        for pronoun in pronouns:
            if pronoun in question_lower:
                if self.conversation_history:
                    last_interaction = self.conversation_history[-1]
                    last_result = last_interaction.get('result', '')
                    
                    try:
                        if last_result.startswith('[') and last_result.endswith(']'):
                            parsed_result = ast.literal_eval(last_result)
                            if parsed_result and isinstance(parsed_result, list):
                                for item in parsed_result:
                                    if isinstance(item, tuple) and len(item) > 0:
                                        name = str(item[0])
                                        resolved_question = resolved_question.replace(pronoun, name)
                                        break
                    except:
                        pass
        
        if "what" in question_lower and ("marks" in question_lower or "grade" in question_lower):
            if self.entity_memory:
                recent_entity = max(self.entity_memory.items(), 
                                  key=lambda x: x[1]['timestamp'])
                entity_name = recent_entity[0]
                
                if not any(name in question_lower for name in self.entity_memory.keys()):
                    resolved_question = f"what are {entity_name}'s marks"
        
        return resolved_question
    
    def get_relevant_context(self, current_question: str) -> str:
        """Get relevant context from memory for the current question"""
        if not self.conversation_history:
            return ""
        
        current_question_lower = current_question.lower()
        relevant_interactions = []
        
        recent_interactions = self.conversation_history[-2:]
        
        for interaction in self.conversation_history:
            question = interaction["question"].lower()
            common_words = set(current_question_lower.split()) & set(question.split())
            if len(common_words) >= 2:
                relevant_interactions.append(interaction)
        
        all_relevant = recent_interactions + relevant_interactions
        
        seen = set()
        unique_relevant = []
        for interaction in all_relevant:
            interaction_id = f"{interaction['question']}_{interaction['timestamp']}"
            if interaction_id not in seen:
                seen.add(interaction_id)
                unique_relevant.append(interaction)
        
        if unique_relevant:
            context_parts = []
            context_parts.append("CONVERSATION CONTEXT (use this to resolve references like 'her', 'his', 'it', etc.):")
            
            for i, interaction in enumerate(unique_relevant[-3:], 1):
                context_parts.append(f"\n{i}. Previous Question: {interaction['question']}")
                context_parts.append(f"   SQL Query: {interaction['query']}")
                context_parts.append(f"   Result: {interaction['result']}")
                context_parts.append(f"   Answer Given: {interaction['answer']}")
            
            if self.entity_memory:
                context_parts.append(f"\nKNOWN ENTITIES: {list(self.entity_memory.keys())}")
            
            return "\n".join(context_parts)
        
        return ""
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """Get a summary of the conversation so far"""
        return {
            "username": self.username,
            "total_interactions": len(self.conversation_history),
            "recent_interactions": self.conversation_history[-5:] if self.conversation_history else [],
            "known_entities": list(self.entity_memory.keys()),
            "question_patterns": list(self.question_patterns.keys())
        }
    
    def clear_memory(self):
        """Clear all memory for this user"""
        self.conversation_history = []
        self.question_patterns = {}
        self.entity_memory = {}
        db_service.clear_user_memory(self.username)

class MemoryManager:
    """Manages memory instances for different users"""
    
    def __init__(self):
        self.user_memories: Dict[str, ConversationMemory] = {}
    
    def get_user_memory(self, username: str) -> ConversationMemory:
        """Get or create memory instance for a user"""
        if username not in self.user_memories:
            self.user_memories[username] = ConversationMemory(username)
        return self.user_memories[username]
    
    def clear_user_memory(self, username: str):
        """Clear memory for a specific user"""
        if username in self.user_memories:
            self.user_memories[username].clear_memory()
            del self.user_memories[username]
        else:
            # Clear from database even if not in memory
            db_service.clear_user_memory(username)
    
    def get_all_users(self) -> List[str]:
        """Get list of all users with memory"""
        return db_service.get_all_users()

# Global memory manager instance
memory_manager = MemoryManager()