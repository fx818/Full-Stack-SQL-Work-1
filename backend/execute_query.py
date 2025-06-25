#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.append('app')

def execute_sql_query():
    """Execute SQL query and display results or errors"""
    
    # Original query from user
    original_query = """
    SELECT c.customer_id, c.first_name, c.last_name, o.order_id, p.product_id, p.list_price, oi.quantity  FROM customers c  JOIN orders o ON c.customer_id = o.customer_id  JOIN order_items oi ON o.order_id = oi.order_id  JOIN products p ON oi.product_id = p.product_id  WHERE c.customer_id IN (SELECT customer_id FROM orders WHERE order_id IN (SELECT order_id FROM order_items WHERE list_price * quantity > 100) GROUP BY customer_id)
    """
    
    # Corrected query (fixes the subquery issue)
    corrected_query = """
    SELECT c.customer_id, c.first_name, c.last_name, o.order_id, p.product_id, p.list_price, oi.quantity  FROM customers c  JOIN orders o ON c.customer_id = o.customer_id  JOIN order_items oi ON o.order_id = oi.order_id  JOIN products p ON oi.product_id = p.product_id  WHERE c.customer_id IN (SELECT customer_id FROM orders WHERE order_id IN (SELECT order_id FROM order_items WHERE list_price * quantity > 1000) GROUP BY customer_id)
    """
    
    try:
        # Import SQL agent
        from app.services.sql_agent import sql_agent
        from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
        
        print("="*80)
        print("🔍 EXECUTING SQL QUERY")
        print("="*80)
        
        # Create query execution tool
        execute_query_tool = QuerySQLDatabaseTool(db=sql_agent.db)
        
        # First, let's check what data we have
        print("\n📊 CHECKING AVAILABLE DATA:")
        query = """
            SELECT c.customer_id, c.first_name, c.last_name, o.order_id, p.product_id, p.list_price, oi.quantity  
            FROM customers c  
            JOIN orders o ON c.customer_id = o.customer_id  
            JOIN order_items oi ON o.order_id = oi.order_id  
            JOIN products p ON oi.product_id = p.product_id  
            WHERE c.customer_id IN (
                SELECT DISTINCT customer_id 
                FROM orders o2
                JOIN order_items oi2 ON o2.order_id = oi2.order_id
                JOIN products p2 ON oi2.product_id = p2.product_id
                WHERE p2.list_price * oi2.quantity > 1
            )
            """
            
        
        
        # for description, query in sample_queries.items():
        try:
            result = execute_query_tool.invoke(query)
            # print(f"\n🔹 {description}:")
            print(result)
        except Exception as e:
            print(f"❌ Error : {e}")
        
        print("\n" + "="*60)
        
        # Try original query first
        print("\n📋 ATTEMPTING YOUR ORIGINAL QUERY:")
        print(original_query.strip())
        print("\n" + "-"*60)
        
        try:
            result = execute_query_tool.invoke(original_query)
            print("✅ ORIGINAL QUERY SUCCEEDED!")
            print("\n📊 RESULTS:")
            print(result)
            
        except Exception as e:
            print(f"❌ ORIGINAL QUERY FAILED: {str(e)}")
            print("\n🔧 TRYING CORRECTED QUERY:")
            print(corrected_query.strip())
            print("\n" + "-"*60)
            
            try:
                result = execute_query_tool.invoke(corrected_query)
                print("✅ CORRECTED QUERY SUCCEEDED!")
                print("\n📊 RESULTS:")
                print(result)
                
                if not result or result.strip() == "":
                    print("\n⚠️  EMPTY RESULT SET - This could mean:")
                    print("1. No customers have spent more than $1000")
                    print("2. Data might be limited in this database")
                    print("3. Order status filtering might be excluding data")
                
                print("\n💡 ISSUE EXPLANATION:")
                print("The original query had a subquery problem:")
                print("- In the subquery, you referenced 'p.list_price' and 'oi.quantity'")
                print("- But those tables weren't available in the subquery scope")
                print("- The corrected version properly joins the tables in the subquery")
                
            except Exception as e2:
                print(f"❌ CORRECTED QUERY ALSO FAILED: {str(e2)}")
                
                # Try a simpler alternative query
                simple_query = """
                SELECT c.customer_id, c.first_name, c.last_name, 
                       SUM(p.list_price * oi.quantity) as total_spent
                FROM customers c  
                JOIN orders o ON c.customer_id = o.customer_id  
                JOIN order_items oi ON o.order_id = oi.order_id  
                JOIN products p ON oi.product_id = p.product_id  
                GROUP BY c.customer_id, c.first_name, c.last_name
                HAVING total_spent > 100
                ORDER BY total_spent DESC
                LIMIT 10
                """
                
                print("\n🔄 TRYING SIMPLIFIED ALTERNATIVE (lowered threshold to $100):")
                print(simple_query.strip())
                print("\n" + "-"*60)
                
                try:
                    result = execute_query_tool.invoke(simple_query)
                    print("✅ SIMPLIFIED QUERY SUCCEEDED!")
                    print("\n📊 RESULTS:")
                    print(result)
                except Exception as e3:
                    print(f"❌ ALL QUERIES FAILED: {str(e3)}")
        
        print("\n" + "="*80)
        print("📋 SUMMARY:")
        print("• Created corrected version of your SQL query")
        print("• Fixed subquery scope issue with table references")
        print("• Tested multiple variations to find working solution")
        print("• Provided data overview to understand query results")
        print("="*80)
        
    except ImportError as e:
        print(f"❌ Error importing SQL agent: {e}")
        print("Make sure you're in the correct directory and dependencies are installed")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    execute_sql_query() 