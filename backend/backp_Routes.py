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

# router = APIRouter()

@router.post("/query", response_model=ApprovalResponse)
async def query_with_human_pause(request: QuestionRequest):
    """Step 1: Generate SQL query, pause before execution"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")

        result = sql_agent.run_until_human_review(request.username, request.question.lower())

        if not result["success"]:
            return ApprovalResponse(
                question=request.question,
                resolved_question=result["resolved_question"],
                query="",
                result="",
                answer=result["answer"],
                success=False,
                error=result["error"]
            )

        # Pickle and hex-encode the intermediate state
        state_bytes = pickle.dumps(result)
        state_hex = state_bytes.hex()

        return ApprovalResponse(
            question=result["question"],
            resolved_question=result["resolved_question"],
            query=result["query"],
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
        state["feedback"] = request.feedback
        
        result = sql_agent.finalize_after_approval(state)

        return QueryResponse(
            question=state.get("question", ""),
            resolved_question=result["resolved_question"],
            query=result["query"],
            result=result["result"],
            answer=result["answer"],
            success=result["success"],
            error=result["error"]
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

        if not result["success"]:
            return ApprovalResponse(
                question=result["question"],
                resolved_question=result["resolved_question"],
                query="",
                result="",
                answer=result["answer"],
                success=False,
                error=result["error"]
            )

        # Serialize updated state
        new_state_bytes = pickle.dumps(result)
        new_state_hex = new_state_bytes.hex()

        return ApprovalResponse(
            question=result["question"],
            resolved_question=result["resolved_question"],
            query=result["query"],
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
    """Health check endpoint"""
    try:
        # Check Supabase connection
        supabase_connected = db_service.health_check()
        
        # Check SQLite database
        database_connected = True
        try:
            sql_agent.db.run("SELECT 1")
        except:
            database_connected = False
        
        return HealthResponse(
            status="healthy" if (supabase_connected and database_connected) else "unhealthy",
            timestamp=datetime.now().isoformat(),
            database_connected=database_connected,
            supabase_connected=supabase_connected
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

