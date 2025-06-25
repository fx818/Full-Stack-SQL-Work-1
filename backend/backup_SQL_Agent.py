import os
import re
import sqlite3
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.utilities import SQLDatabase
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict, NotRequired

from core.config import settings
from services.memory_service import memory_manager

# State structure
class State(TypedDict):
    username: str
    question: str
    query: str
    error: str
    success: bool
    result: str
    answer: str
    context_from_memory: str
    resolved_question: str
    feedback: NotRequired[str]

class SQLAgent:
    def __init__(self):
        self.llm = ChatOpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=settings.API_KEY,
            model="llama-3.1-8b-instant",
            temperature=0,
        )
        
        # Initialize SQLite database
        self.setup_sqlite_database()
        self.db = SQLDatabase.from_uri(f"sqlite:///{settings.SQLITE_DB_PATH}")
        
        # Build the graph
        self.graph = self.build_graph()
    
    def setup_sqlite_database(self):
        """Setup SQLite database by converting text columns to lowercase"""
        def convert_all_text_columns_to_lowercase(db_path: str):
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"PRAGMA table_info({table});")
                columns_info = cursor.fetchall()
                text_columns = [col[1] for col in columns_info if "CHAR" in col[2].upper() or "TEXT" in col[2].upper()]

                for col in text_columns:
                    try:
                        update_query = f"UPDATE {table} SET {col} = LOWER({col}) WHERE {col} IS NOT NULL;"
                        cursor.execute(update_query)
                    except Exception as e:
                        print(f"Error updating {table}.{col}: {e}")

            conn.commit()
            conn.close()
        
        convert_all_text_columns_to_lowercase(settings.SQLITE_DB_PATH)
    
    def get_table_info_str(self):
        """Get all table information from the database as a string"""
        table_infos = []
        try:
            # Get all table names from sqlite_master
            query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
            result = self.db.run(query)
            
            # Handle different result formats
            tables = []
            if isinstance(result, str):
                # If result is a string, try to parse it
                import ast
                try:
                    parsed_result = ast.literal_eval(result)
                    if isinstance(parsed_result, list):
                        tables = [row[0] if isinstance(row, tuple) else row for row in parsed_result]
                except:
                    # If parsing fails, try splitting the string
                    lines = result.strip().split('\n')
                    tables = [line.strip() for line in lines if line.strip()]
            elif isinstance(result, list):
                # If result is a list, extract table names
                for row in result:
                    if isinstance(row, tuple) and len(row) > 0:
                        tables.append(row[0])
                    elif isinstance(row, dict) and 'name' in row:
                        tables.append(row['name'])
                    elif isinstance(row, str):
                        tables.append(row)
            
            for table in tables:
                if not table or not isinstance(table, str):
                    continue
                    
                try:
                    columns_info_result = self.db.run(f"PRAGMA table_info({table});")
                    columns_with_types = []
                    columns_only = []
                    
                    # Parse column info
                    columns_info = []
                    if isinstance(columns_info_result, str):
                        # Try to parse string result
                        try:
                            import ast
                            columns_info = ast.literal_eval(columns_info_result)
                        except:
                            continue
                    elif isinstance(columns_info_result, list):
                        columns_info = columns_info_result
                    
                    if columns_info and isinstance(columns_info, list) and len(columns_info) > 0:
                        for col in columns_info:
                            try:
                                if isinstance(col, tuple) and len(col) >= 3:
                                    # col: (cid, name, type, notnull, dflt_value, pk)
                                    columns_with_types.append(f"{col[1]} ({col[2]})")
                                    columns_only.append(col[1])
                                elif isinstance(col, dict):
                                    name = col.get('name', '')
                                    col_type = col.get('type', '')
                                    if name:
                                        columns_with_types.append(f"{name} ({col_type})")
                                        columns_only.append(name)
                            except (IndexError, TypeError):
                                continue
                    
                    if columns_only:  # Only add table if we found columns
                        table_info = f"Table '{table}':\n"
                        table_info += f"  Columns: {', '.join(str(col) for col in columns_only)}\n"
                        table_info += f"  Detailed: {', '.join(str(col) for col in columns_with_types)}"
                        table_infos.append(table_info)
                        
                except Exception as e:
                    print(f"Error getting info for table {table}: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error getting table info: {e}")
            # Fallback to basic table list
            return "Database tables: products, customers, orders, order_items, stores, staffs, categories, brands, stocks"
            
        return "\n\n".join(table_infos) if table_infos else "No tables found in database"
    
    def validate_and_fix_query(self, query: str) -> str:
        """Validate and fix common SQL query issues"""
        query = query.strip()
        
        if query.upper().startswith(('UPDATE', 'INSERT', 'DELETE')):
            query = re.sub(r'\s+LIMIT\s+\d+\s*$', '', query, flags=re.IGNORECASE)
        
        # if "\n" in query:
        query = query.replace("\n", " ")
        
            
        print("query", query)
        
        return query
    
    def add_memory_context(self, state: State):
        """Add relevant memory context and resolve contextual references"""
        user_memory = memory_manager.get_user_memory(state["username"])
        resolved_question = user_memory.resolve_contextual_references(state["question"])
        context = user_memory.get_relevant_context(state["question"])
        
        return {
            "context_from_memory": context,
            "resolved_question": resolved_question
        }
    
    def write_query(self, state: State) -> State:
        """Generate SQL query from natural language question"""
        table_info = self.get_table_info_str()
        memory_context = state.get("context_from_memory", "")
        print("memory_context", memory_context)
        feedback = state.get("feedback", "") 
        resolved_question = state.get("resolved_question", state["question"])
        # print("table_info", table_info)
        
        system_message = """
You are an expert SQL query generator with memory of previous interactions. Your task is to generate a syntactically correct {dialect} SQL query from the user's natural language question.

{memory_context}

CRITICAL RULES FOR MEMORY AND CONTEXT:
1. ALWAYS pay close attention to the conversation context above.
2. If the question contains pronouns (her, his, their, it, she, he, they), use the context to identify what they refer to.
3. If the question refers to a person or entity mentioned in previous interactions, use that information.
4. The resolved question should guide your SQL generation: {resolved_question}

CRITICAL SQL RULES:
1. Use ONLY the exact table names and column names provided in the schema below.
2. Column names are case-sensitive — use exact capitalization as shown.
3. Never assume or invent column names — only use those explicitly listed.
4. Do NOT use SELECT * — always specify only the relevant columns.
5. Unless the question explicitly requests more, limit the result to {top_k} rows.
6. For date/time filtering or extraction, use correct functions per dialect:
   - SQLite: strftime('%Y', column), strftime('%m', column)
   - MySQL: YEAR(column), MONTH(column), DAY(column)
   - PostgreSQL: EXTRACT(YEAR FROM column), EXTRACT(MONTH FROM column)
7. For text matching, use LIKE with `%` wildcards (e.g., WHERE name LIKE '%john%').
8. When searching by name, always use the column named 'name' (not 'username', etc.).
9. Do not use aliases, subqueries, or joins unless necessary to answer the question.
10. Only include valid SQL syntax for the specified dialect.
11. Use lowercase for text values in WHERE clauses since all text data is stored in lowercase.
12. When searching by id, check the column name for 'user_id', 'student_id', etc., and use it exactly as shown in the schema.

IMPORTANT:
- ALWAYS consider the conversation context when interpreting the question.
- If a pronoun or reference is unclear, look at the previous interactions to resolve it.
- The resolved question "{resolved_question}" should be your primary guide.

DATABASE SCHEMA:
{table_info}

Convert the following user question into a valid SQL query, considering the conversation context and resolved question.

Only output the SQL query — no explanations, no markdown formatting.

ORIGINAL QUESTION: {input}
RESOLVED QUESTION: {resolved_question}
"""

        user_prompt = "Question: {input} \n\n Use this feedback to improve the query: {feedback} -> It is very important to keep in mind if feedback is present"
        
        query_prompt_template = ChatPromptTemplate.from_messages(
            [("system", system_message), ("human", user_prompt)]
        )
        
        messages = query_prompt_template.format_messages(
            dialect=self.db.dialect,
            top_k=10,
            table_info=table_info,
            memory_context=memory_context,
            resolved_question=resolved_question,
            input=state["question"],
            feedback=feedback or ""
        )
        
        raw_response = self.llm.invoke(messages)
        # Handle different response types
        if hasattr(raw_response, 'content'):
            if isinstance(raw_response.content, str):
                response_text = raw_response.content.strip()
            elif isinstance(raw_response.content, list):
                response_text = str(raw_response.content[0]).strip() if raw_response.content else ""
            else:
                response_text = str(raw_response.content).strip()
        else:
            response_text = str(raw_response).strip()

        match = re.search(r"```sql\s+(.*?)```", response_text, re.DOTALL)
        if match:
            sql_query = match.group(1).strip()
        else:
            sql_query = response_text.strip()

        sql_query = self.validate_and_fix_query(sql_query)
        
        state["query"] = sql_query
        
        return state
        # return {"query": sql_query}
    
    def execute_query(self, state: State) -> State:
        """Execute SQL query and return results"""
        execute_query_tool = QuerySQLDatabaseTool(db=self.db)
        try:
            result = execute_query_tool.invoke(state["query"])
            state["result"] = result
            return state
            # return {"result": result}
        except Exception as e:
            state["result"] = f"Error executing query: {str(e)}"
            return state
            # return {"result": f"Error executing query: {str(e)}"}
    
    def generate_answer(self, state: State) -> State:
        
        """Answer question using retrieved information and memory context"""
        memory_context = state.get("context_from_memory", "")
        resolved_question = state.get("resolved_question", state.get("question", ""))

        prompt = (
            "You are a helpful assistant that answers questions based on database query results and conversation history. "
            "Use the SQL result to provide a direct, natural language answer to the user's question. "
            "Consider the conversation history when relevant, and acknowledge when you're building on previous information. "
            "Do not suggest query modifications or provide technical explanations unless asked.\n\n"
            f'Original Question: {state["question"]}\n'
            f'Resolved Question: {resolved_question}\n'
            f'SQL Query Used: {state["query"]}\n'
            f'SQL Result: {state["result"]}\n\n'
            f'Feedback: {state["feedback"]}\n\n'
        )

        if memory_context:
            prompt += f'Conversation Context:\n{memory_context}\n\n'
        
        prompt += "Please provide a clear, direct answer to the user's question using the information from the SQL result."
        
        response = self.llm.invoke(prompt)
        # Handle different response types
        if hasattr(response, 'content'):
            if isinstance(response.content, str):
                answer = response.content.strip()
            elif isinstance(response.content, list):
                answer = str(response.content[0]).strip() if response.content else ""
            else:
                answer = str(response.content).strip()
        else:
            answer = str(response).strip()
        
        # Store this interaction in memory
        user_memory = memory_manager.get_user_memory(state["username"])
        user_memory.add_interaction(
            question=state["question"],
            query=state["query"],
            result=state["result"],
            answer=answer
        )
        state["answer"] = answer
        state['context_from_memory'] = memory_context
        return state
        # return {"answer": answer}
    
    # def build_graph(self):
    #     """Build the state graph for processing queries"""
    #     graph_builder = StateGraph(State).add_sequence(
    #         [self.add_memory_context, self.write_query, self.execute_query, self.generate_answer]
    #     )
    #     graph_builder.add_edge(START, "add_memory_context")
    #     return graph_builder.compile()
    
    # def process_question(self, username: str, question: str) -> Dict[str, Any]:
    #     """Process a question through the complete pipeline"""
    #     initial_state = State(
    #         username=username,
    #         question=question, 
    #         query="", 
    #         result="", 
    #         answer="",
    #         context_from_memory="",
    #         resolved_question=""
    #     )
        
    #     try:
    #         final_state = None
    #         for state_update in self.graph.stream(initial_state):
    #             final_state = state_update
            
    #         if final_state is None:
    #             raise ValueError("Graph did not yield any states.")
            
    #         # Extract the final values from the nested state structure
    #         result_state = final_state.get("generate_answer", final_state)
            
    #         return {
    #             "success": True,
    #             "question": question,
    #             "resolved_question": result_state.get("resolved_question", question),
    #             "sql_query": result_state.get("query", ""),
    #             "result": result_state.get("result", ""),
    #             "answer": result_state.get("answer", ""),
    #             "error": None
    #         }
            
    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "question": question,
    #             "resolved_question": question,
    #             "sql_query": "",
    #             "result": "",
    #             "answer": f"Error processing question: {str(e)}",
    #             "error": str(e)
    #         }


    # def build_graph(self):
    #     """Build the state graph with a pause for human review before executing the query"""
    #     graph_builder = StateGraph(State).add_node("add_memory_context", self.add_memory_context)
    #     graph_builder.add_node("write_query", self.write_query)
    #     graph_builder.add_node("execute_query", self.execute_query)
    #     graph_builder.add_node("generate_answer", self.generate_answer)

    #     graph_builder.set_entry_point("add_memory_context")
    #     graph_builder.add_edge("add_memory_context", "write_query")
    #     # Human will approve before moving from write_query to execute_query
    #     graph_builder.add_edge("execute_query", "generate_answer")

    #     return graph_builder.compile()
    
    # def run_until_human_review(self, username: str, question: str) -> Dict[str, Any]:
    #     """Run the graph until query is written and pause for human review."""
    #     initial_state = State(
    #         username=username,
    #         question=question,
    #         query="", 
    #         result="", 
    #         answer="", 
    #         context_from_memory="", 
    #         resolved_question=""
    #     )

    #     try:
    #         state_stream = self.graph.stream(initial_state)
    #         state_before_exec = None

    #         for state_update in state_stream:
    #             state_before_exec = state_update
    #             if "write_query" in state_update:
    #                 break  # Stop after write_query for human review

    #         if state_before_exec is None:
    #             raise ValueError("Failed to generate SQL query.")

    #         query_state = state_before_exec.get("write_query", state_before_exec)

    #         return {
    #             "success": True,
    #             "stage": "awaiting_approval",
    #             "question": question,
    #             "resolved_question": query_state.get("resolved_question", question),
    #             "sql_query": query_state.get("query", ""),
    #             "state": state_before_exec,  # Save this for next step
    #             "message": "Query ready for human review."
    #         }

    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "stage": "error",
    #             "question": question,
    #             "resolved_question": question,
    #             "sql_query": "",
    #             "result": "",
    #             "answer": f"Error generating query: {str(e)}",
    #             "error": str(e)
    #         }
            
    # def resume_after_approval(self, state_after_write: State) -> Dict[str, Any]:
    #     """Resume from execute_query → generate_answer after approval"""
    #     current_state = state_after_write.get("write_query", state_after_write)
    #     try:
    #         # Extract inner node from write_query if present

    #         # Manually execute the remaining nodes
    #         executed_state = self.execute_query(current_state)
    #         final_state = self.generate_answer(executed_state)

    #         return {
    #             "success": True,
    #             "stage": "completed",
    #             "question": final_state.get("question", ""),
    #             "resolved_question": final_state.get("resolved_question", ""),
    #             "sql_query": final_state.get("query", ""),
    #             "result": final_state.get("result", ""),
    #             "answer": final_state.get("answer", ""),
    #             "error": None
    #         }

    #     except Exception as e:
    #         # Also safely extract current_state
    #         question = current_state.get("question", "") if 'current_state' in locals() else ""
    #         resolved = current_state.get("resolved_question", "") if 'current_state' in locals() else ""
    #         sql_query = current_state.get("query", "") if 'current_state' in locals() else ""

    #         return {
    #             "success": False,
    #             "stage": "error",
    #             "question": question,
    #             "resolved_question": resolved,
    #             "sql_query": sql_query,
    #             "result": "",
    #             "answer": f"Error resuming execution: {str(e)}",
    #             "error": str(e)
    #         }


    # def build_graph(self):
    #     """Build graph up to the query execution point"""
    #     graph_builder = StateGraph(State)
    #     graph_builder.add_node("add_memory_context", self.add_memory_context)
    #     graph_builder.add_node("write_query", self.write_query)
    #     graph_builder.add_node("execute_query", self.execute_query)
    #     graph_builder.add_node("generate_answer", self.generate_answer)

    #     graph_builder.set_entry_point("add_memory_context")
    #     graph_builder.add_edge("add_memory_context", "write_query")
    #     graph_builder.add_edge("execute_query", "generate_answer")

    #     return graph_builder.compile()

    # def run_until_human_review(self, username: str, question: str) -> Dict[str, Any]:
    #     """Run until write_query is done, pause for human approval"""
    #     initial_state = State(
    #         username=username,
    #         question=question,
    #         query="", 
    #         result="", 
    #         answer="",
    #         context_from_memory="", 
    #         resolved_question="",
    #         feedback=""
    #     )
    #     # print("Line 1")

    #     try:
    #         state_stream = self.graph.stream(initial_state)
    #         final_before_pause = None
    #         # print("Line 2")

    #         for step in state_stream:
    #             final_before_pause = step
    #             if "write_query" in step:
    #                 break
    #         # print("Line 3")

    #         if not final_before_pause:
    #             raise ValueError("No output from write_query")
    #         # print("Line 4")

    #         write_query_state = final_before_pause.get("write_query", final_before_pause)
    #         # print("Line 5")

    #         return {
    #             "success": True,
    #             "question": question,
    #             "resolved_question": write_query_state.get("resolved_question", ""),
    #             "sql_query": write_query_state.get("query", ""),
    #             "answer": "Query generated and pending human approval.",
    #             "state": final_before_pause
    #         }
            

    #     except Exception as e:
    #         return {
    #             "success": False,
    #             "question": question,
    #             "resolved_question": question,
    #             "sql_query": "",
    #             "result": "",
    #             "answer": f"Error during write_query: {str(e)}",
    #             "error": str(e)
    #         }
            
    # def resume_after_approval(self, state_after_write: State, feedback: Optional[str] = "") -> Dict[str, Any]:
    #     """Resume execution manually after human approves the query"""
    #     try:
    #         # Extract from "write_query" node if present
    #         current_state = state_after_write.get("write_query", state_after_write)
    #         print("current_state", current_state)

    #         executed = self.execute_query(current_state)

    #         # executed_state = State(
    #         #     username=current_state.get("username", ""),
    #         #     question=current_state.get("question", ""),
    #         #     query=current_state.get("sql_query", ""), 
    #         #     result=executed.get("result", ""), 
    #         #     answer="",
    #         #     context_from_memory="", 
    #         #     resolved_question=current_state.get("resolved_question", ""),
    #         #     feedback=feedback
    #         # )
            
    #         executed_state = State(
    #             username=current_state.get("username", ""),
    #             question=current_state.get("question", ""),
    #             query=current_state.get("query", ""),
    #             result=executed.get("result", ""),
    #             answer="",
    #             context_from_memory="",
    #             resolved_question=current_state.get("resolved_question", ""),
    #             feedback=feedback  # ✅ Add this
    #         )
            
    #         final = self.generate_answer(executed_state)
    #         return {
    #             "success": True,
    #             "question": executed_state.get("question", ""),
    #             "resolved_question": executed_state.get("resolved_question", ""),
    #             "sql_query": executed_state.get("query", ""),
    #             "result": executed_state.get("result", ""),
    #             "answer": final.get("answer", ""),
    #             "error": None
    #         }
          

    #     except Exception as e:
    #         fallback = locals().get("current_state", {})
    #         return {
    #             "success": False,
    #             "question": fallback.get("question", ""),
    #             "resolved_question": fallback.get("resolved_question", ""),
    #             "sql_query": fallback.get("query", ""),
    #             "result": "",
    #             "answer": f"Error resuming execution: {str(e)}",
    #             "error": str(e)
    #         }
    
    # def should_continue(self, state: State) -> bool:
        # """Check if the agent should continue based on the state"""
        # feedback = state.get("feedback", "")
        # if feedback == "":
        #     return True
        # else:
        #     return False

    
    def build_graph(self):
        """Build graph up to the query execution point"""
        graph_builder = StateGraph(State)
        graph_builder.add_node("add_memory_context", self.add_memory_context)
        graph_builder.add_node("write_query", self.write_query)
        graph_builder.add_node("execute_query", self.execute_query)
        graph_builder.add_node("generate_answer", self.generate_answer)

        graph_builder.set_entry_point("add_memory_context")
        graph_builder.add_edge("add_memory_context", "write_query")
        # graph_builder.add_conditional_edges(
        #     "write_query", 
        #     self.should_continue,
        #     {
        #         True: "execute_query",
        #         False: "write_query"
        #     }
        # )
        graph_builder.add_edge("execute_query", "generate_answer")

        return graph_builder.compile()




    def run_until_human_review(self, username: str, question: str) -> State:
        """Run until write_query is done, pause for human approval"""
        initial_state = State(
            username=username,
            question=question,
            query="",
            result="",
            answer="",
            error="",
            success=True,
            context_from_memory="",
            resolved_question="",
            feedback=""
        )

        try:
            state_stream = self.graph.stream(initial_state)
            final_before_pause = None

            for step in state_stream:
                final_before_pause = step
                if "write_query" in step:
                    break

            if not final_before_pause:
                raise ValueError("No output from write_query")

            # Extract the state from the final step
            if isinstance(final_before_pause, dict) and "write_query" in final_before_pause:
                return final_before_pause["write_query"]
            elif isinstance(final_before_pause, dict):
                # If it's a flat dict, convert to State
                return State(**final_before_pause)
            else:
                return final_before_pause

        except Exception as e:
            return State(
                username=username,
                question=question,
                query="",
                result="",
                answer=f"Error during write_query: {str(e)}",
                error=str(e),
                success=False,
                context_from_memory="",
                resolved_question=question,
                feedback=""
            )


    # def resume_after_approval(self, state_before_write: State, feedback: Optional[str] = "") -> State:
    #     """Resume execution manually after human feedback and regenerate query if needed"""
    #     try:
    #         # Extract state before write_query
    #         current_state = state_before_write.get("add_memory_context", state_before_write)

    #         # Update question with feedback if provided
    #         if feedback:
    #             updated_question = f"{current_state['question'].strip()} ({feedback.strip()})"
    #         else:
    #             updated_question = current_state['question']

    #         # Rebuild state with possibly modified question
    #         updated_state = State(
    #             username=current_state.get("username", ""),
    #             question=updated_question,
    #             context_from_memory=current_state.get("context_from_memory", ""),
    #             query="",
    #             result="",
    #             answer="",
    #             error="",
    #             success=True,
    #             resolved_question="",
    #             feedback=feedback
    #         )
      
    #         # Re-run write_query to regenerate SQL with updated question
    #         query_state = self.write_query(updated_state)

    #         # Continue execution
    #         executed_state = self.execute_query(query_state)
    #         final_state = self.generate_answer({
    #             **executed_state,
    #             "feedback": feedback
    #         })
            
    #         return final_state
    #     except Exception as e:
    #         # Safely get current_state if it exists, otherwise use empty defaults
    #         current_state = state_before_write.get("add_memory_context", state_before_write)
    #         username = ""
    #         question = ""
    #         resolved_question = ""
            
    #         if 'current_state' in locals():
    #             username = current_state.get("username", "")
    #             question = current_state.get("question", "")
    #             resolved_question = current_state.get("resolved_question", "")
            
    #         return State(
    #             username=username,
    #             question=question,
    #             resolved_question=resolved_question,
    #             query="",
    #             result="",
    #             error=str(e),
    #             success=False,
    #             answer=f"Error after feedback: {str(e)}",
    #             context_from_memory="",
    #             feedback=feedback
    #         )

    def regenerate_query_with_feedback(self, state_before_write: State, feedback: Optional[str] = "") -> State:
        """Update the question with feedback and regenerate the query"""
        try:
            current_state = state_before_write.get("add_memory_context", state_before_write)
            updated_question = f"{current_state['question'].strip()} ({feedback.strip()})" if feedback else current_state['question']

            updated_state = State(
                username=current_state.get("username", ""),
                question=updated_question,
                context_from_memory=current_state.get("context_from_memory", ""),
                query="",
                result="",
                answer="",
                error="",
                success=True,
                resolved_question="",
                feedback=feedback
            )

            return self.write_query(updated_state)

        except Exception as e:
            return State(
                username=current_state.get("username", ""),
                question=current_state.get("question", ""),
                resolved_question=current_state.get("resolved_question", ""),
                query="",
                result="",
                answer=f"Error during regeneration: {str(e)}",
                error=str(e),
                success=False,
                context_from_memory=current_state.get("context_from_memory", ""),
                feedback=feedback
            )

    def finalize_after_approval(self, query_state: State) -> State:
        """Continue execution after final feedback approval"""
        try:
            executed_state = self.execute_query(query_state)
            final_state = self.generate_answer({
                **executed_state,
                "feedback": query_state.get("feedback", "")
            })
            return final_state
        except Exception as e:
            return State(
                username=query_state.get("username", ""),
                question=query_state.get("question", ""),
                resolved_question=query_state.get("resolved_question", ""),
                query=query_state.get("query", ""),
                result="",
                answer=f"Error during final execution: {str(e)}",
                error=str(e),
                success=False,
                context_from_memory=query_state.get("context_from_memory", ""),
                feedback=query_state.get("feedback", "")
            )


# Global SQL Agent instance
sql_agent = SQLAgent()