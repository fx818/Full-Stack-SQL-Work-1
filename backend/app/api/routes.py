from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict, Any

from models.request_response import (
    QuestionRequest, QueryResponse, MemoryCommandRequest, 
    MemoryResponse, HealthResponse
)
from services.sql_agent import sql_agent
from services.memory_service import memory_manager
from services.database import db_service

router = APIRouter()

# @router.post("/query", response_model=QueryResponse)
# async def process_query(request: QuestionRequest):
#     """Process a natural language question and return SQL query results"""
#     try:
#         if not request.question.strip():
#             raise HTTPException(status_code=400, detail="Question cannot be empty")
        
#         result = sql_agent.process_question(request.username, request.question.lower())
        
#         return QueryResponse(
#             question=result["question"],
#             resolved_question=result["resolved_question"],
#             query=result["query"],
#             result=result["result"],
#             answer=result["answer"],
#             success=result["success"],
#             error=result["error"]
#         )
        
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# from fastapi import APIRouter, HTTPException

import pickle
from models.request_response import ApprovalResponse, QueryApprovalRequest
from fastapi.responses import JSONResponse
from typing import Union

# router = APIRouter()

# New API Flow:
# 1. POST /query - Handles both chat and SQL intents
#    - Chat intents: Returns immediate QueryResponse 
#    - SQL intents: Returns ApprovalResponse requiring human review
# 2. POST /query/approve - Executes approved SQL query
# 3. POST /query/regenerate - Regenerates SQL query with feedback

@router.post("/query", response_model=Union[QueryResponse, ApprovalResponse])
async def process_query(request: QuestionRequest):
    """Process a question - returns immediate response for chat, approval required for SQL"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        result = sql_agent.run_until_human_review(request.username, request.question.lower())

        if not result.get("success", True):
            return QueryResponse(
                question=request.question,
                resolved_question=result.get("resolved_question", request.question),
                query="",
                result="",
                answer=result.get("answer", "Error processing request"),
                success=False,
                error=result.get("error", "Unknown error")
            )

        # Check if this was a chat interaction (immediate response)
        intent = result.get("intent", "")
        if intent == "chat" or result.get("answer", "") and not result.get("query", ""):
            # Chat interaction - return complete response immediately
            return QueryResponse(
                question=result.get("question", request.question),
                resolved_question=result.get("resolved_question", request.question),
                query="",  # No SQL query for chat
                result="",  # No SQL result for chat
                answer=result.get("answer", ""),
                success=True,
                error=None
            )
        
        # SQL interaction - return approval response for human review
        # Pickle and hex-encode the intermediate state
        state_bytes = pickle.dumps(result)
        state_hex = state_bytes.hex()

        return ApprovalResponse(
            question=result.get("question", request.question),
            resolved_question=result.get("resolved_question", request.question),
            query=result.get("query", ""),
            result=None,
            answer="Query generated and pending human approval.",
            success=True,
            error=None,
            message="Please review and approve the query to proceed.",
            state_hex=state_hex
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/query/approve", response_model=QueryResponse)
async def approve_and_execute_query(request: QueryApprovalRequest):
    """Step 2: Resume graph execution after human approval"""
    try:
        # Unpickle the state
        state_bytes = bytes.fromhex(request.state_hex)
        state = pickle.loads(state_bytes)
        
        # Add feedback to the state if provided
        if request.feedback:
            state["feedback"] = request.feedback
        
        result = sql_agent.finalize_after_approval(state)

        return QueryResponse(
            question=result.get("question", state.get("question", "")),
            resolved_question=result.get("resolved_question", state.get("resolved_question", "")),
            query=result.get("query", ""),
            result=result.get("result", ""),
            answer=result.get("answer", ""),
            success=result.get("success", True),
            error=result.get("error", None)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.post("/query/regenerate", response_model=ApprovalResponse)
async def regenerate_query_with_feedback(request: QueryApprovalRequest):
    """Regenerate SQL based on feedback, allowing multiple review cycles"""
    try:
        state_bytes = bytes.fromhex(request.state_hex)
        state = pickle.loads(state_bytes)

        # Regenerate only the query using feedback
        result = sql_agent.regenerate_query_with_feedback(state, request.feedback)

        if not result.get("success", True):
            return ApprovalResponse(
                question=result.get("question", ""),
                resolved_question=result.get("resolved_question", ""),
                query="",
                result="",
                answer=result.get("answer", "Error regenerating query"),
                success=False,
                error=result.get("error", "Unknown error")
            )

        # Serialize updated state
        new_state_bytes = pickle.dumps(result)
        new_state_hex = new_state_bytes.hex()

        return ApprovalResponse(
            question=result.get("question", ""),
            resolved_question=result.get("resolved_question", ""),
            query=result.get("query", ""),
            result=None,
            answer="Query regenerated. You can approve or provide more feedback.",
            success=True,
            error=None,
            message="Please review the new query.",
            state_hex=new_state_hex
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")



@router.post("/memory/command", response_model=MemoryResponse)
async def handle_memory_command(request: MemoryCommandRequest):
    """Handle memory-related commands"""
    try:
        command = request.command.lower().strip()
        username = request.username
        
        if command == "/history":
            user_memory = memory_manager.get_user_memory(username)
            summary = user_memory.get_conversation_summary()
            return MemoryResponse(
                success=True,
                message="Conversation history retrieved successfully",
                data=summary
            )
        
        elif command == "/clear":
            memory_manager.clear_user_memory(username)
            return MemoryResponse(
                success=True,
                message="Memory cleared successfully"
            )
        
        elif command == "/entities":
            user_memory = memory_manager.get_user_memory(username)
            entities = list(user_memory.entity_memory.keys())
            return MemoryResponse(
                success=True,
                message="Known entities retrieved successfully",
                data={"entities": entities}
            )
        
        elif command == "/summary":
            user_memory = memory_manager.get_user_memory(username)
            summary = user_memory.get_conversation_summary()
            return MemoryResponse(
                success=True,
                message="Conversation summary retrieved successfully",
                data=summary
            )
        
        elif command == "/users":
            users = memory_manager.get_all_users()
            return MemoryResponse(
                success=True,
                message="All users retrieved successfully",
                data={"users": users}
            )
        
        else:
            return MemoryResponse(
                success=False,
                message=f"Unknown command: {command}. Available commands: /history, /clear, /entities, /summary, /users"
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing memory command: {str(e)}")

@router.get("/memory/{username}/history")
async def get_user_history(username: str):
    """Get conversation history for a specific user"""
    try:
        user_memory = memory_manager.get_user_memory(username)
        summary = user_memory.get_conversation_summary()
        return {
            "success": True,
            "username": username,
            "data": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving user history: {str(e)}")

@router.delete("/memory/{username}")
async def clear_user_memory(username: str):
    """Clear memory for a specific user"""
    try:
        memory_manager.clear_user_memory(username)
        return {
            "success": True,
            "message": f"Memory cleared for user: {username}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing user memory: {str(e)}")

@router.get("/users")
async def get_all_users():
    """Get list of all users with conversation memory"""
    try:
        users = memory_manager.get_all_users()
        return {
            "success": True,
            "users": users,
            "total_users": len(users)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving users: {str(e)}")

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Check system health status"""
    try:
        # Check database connectivity
        db_connected = False
        supabase_connected = False
        
        try:
            # Test SQL agent DB connection
            from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
            execute_query_tool = QuerySQLDatabaseTool(db=sql_agent.db)
            result = execute_query_tool.invoke("SELECT 1")
            db_connected = True
        except Exception as e:
            print(f"Database connection failed: {e}")
        
        try:
            # Test Supabase connection
            if db_service and db_service.connection:
                with db_service.connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                supabase_connected = True
        except Exception as e:
            print(f"Supabase connection failed: {e}")
        
        status = "healthy" if db_connected else "unhealthy"
        
        return HealthResponse(
            status=status,
            database_connected=db_connected,
            supabase_connected=supabase_connected,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            database_connected=False,
            supabase_connected=False,
            timestamp=datetime.now().isoformat()
        )

@router.get("/schema")
async def get_database_schema():
    """Get database schema information"""
    try:
        # Get raw schema info from SQL agent
        table_info_str = sql_agent.get_table_info_str()
        
        # Parse the string into a structured format for the frontend
        schema_data = {}
        
        # Split by double newlines to get individual table info blocks
        table_blocks = table_info_str.split('\n\n')
        
        for block in table_blocks:
            
            if not block.strip():
                continue
                
            lines = block.strip().split('\n')
            if not lines:
                continue
                
            # Extract table name from first line (format: "Table 'tablename':")
            first_line = lines[0]
            if "Table '" in first_line and "':" in first_line:
                table_name = first_line.split("Table '")[1].split("':")[0]
                
                # Initialize table data
                columns = []
                
                # Process remaining lines to extract column information
                for line in lines[1:]:
                    if line.strip().startswith("Detailed:"):
                        # Parse detailed column info (format: "column_name (TYPE)")
                        detailed_info = line.split("Detailed:")[1].strip()
                        if detailed_info:
                            # Split by comma and parse each column
                            column_entries = detailed_info.split(', ')
                            for entry in column_entries:
                                entry = entry.strip()
                                if '(' in entry and ')' in entry:
                                    # Extract column name and type
                                    name = entry.split('(')[0].strip()
                                    col_type = entry.split('(')[1].split(')')[0].strip()
                                    
                                    # Create column info
                                    column_info = {
                                        "name": name,
                                        "type": col_type,
                                        "nullable": True,  # Default, could be enhanced
                                        "primary_key": False  # Could be enhanced by parsing PRAGMA info
                                    }
                                    columns.append(column_info)
                
                # Add table to schema if we found columns
                if columns:
                    schema_data[table_name] = columns
        
        return JSONResponse(content={
            "success": True,
            "schema": schema_data,
            "message": f"Found {len(schema_data)} tables in database",
            "raw_info": table_info_str  # Include raw info for debugging
        })
        
    except Exception as e:
        print(f"Error getting schema: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "schema": {},
                "message": f"Error retrieving database schema: {str(e)}",
                "raw_info": ""
            }
        )

