#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.append('app')

def main():
    print("🚀 SQL QUERY DIAGNOSTICS & EXECUTION")
    print("="*80)
    
    try:
        from services.sql_agent import sql_agent
        from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
        
        execute_query_tool = QuerySQLDatabaseTool(db=sql_agent.db)
        
        # 1. Basic data check
        print("\n📊 DATABASE OVERVIEW:")
        basic_queries = {
            "Customers": "SELECT COUNT(*) FROM customers",
            "Orders": "SELECT COUNT(*) FROM orders", 
            "Order Items": "SELECT COUNT(*) FROM order_items",
            "Products": "SELECT COUNT(*) FROM products"
        }
        
        for name, query in basic_queries.items():
            try:
                result = execute_query_tool.invoke(query)
                print(f"• {name}: {result}")
            except Exception as e:
                print(f"• {name}: Error - {e}")
        
        # 2. Sample data
        print("\n🔍 SAMPLE DATA:")
        sample_query = """
        SELECT c.customer_id, c.first_name, c.last_name, 
               o.order_id, p.product_name, p.list_price, oi.quantity
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        JOIN order_items oi ON o.order_id = oi.order_id
        JOIN products p ON oi.product_id = p.product_id
        LIMIT 5
        """
        
        try:
            result = execute_query_tool.invoke(sample_query)
            print("Sample joined data:")
            print(result)
        except Exception as e:
            print(f"Sample data error: {e}")
        
        # 3. Your original query (FIXED)
        print("\n" + "="*60)
        print("🎯 YOUR ORIGINAL QUERY - FIXED VERSION:")
        
        your_fixed_query = """
        SELECT c.customer_id, c.first_name, c.last_name, o.order_id, 
               p.product_id, p.list_price, oi.quantity,
               (p.list_price * oi.quantity) as line_total
        FROM customers c  
        JOIN orders o ON c.customer_id = o.customer_id  
        JOIN order_items oi ON o.order_id = oi.order_id  
        JOIN products p ON oi.product_id = p.product_id  
        WHERE c.customer_id IN (
            SELECT o2.customer_id 
            FROM orders o2 
            JOIN order_items oi2 ON o2.order_id = oi2.order_id 
            JOIN products p2 ON oi2.product_id = p2.product_id 
            GROUP BY o2.customer_id 
            HAVING SUM(p2.list_price * oi2.quantity) > 500
        )
        ORDER BY c.customer_id, line_total DESC
        LIMIT 10
        """
        
        print("Fixed Query:")
        print(your_fixed_query)
        print("\n" + "-"*60)
        
        try:
            result = execute_query_tool.invoke(your_fixed_query)
            if result and result.strip():
                print("✅ SUCCESS! Results:")
                print(result)
            else:
                print("⚠️ Query executed but returned no results.")
                print("Trying with lower threshold...")
                
                # Try with lower threshold
                lower_threshold_query = your_fixed_query.replace("> 500", "> 100")
                result2 = execute_query_tool.invoke(lower_threshold_query)
                if result2 and result2.strip():
                    print("✅ SUCCESS with $100 threshold:")
                    print(result2)
                else:
                    print("Still no results. Let's check customer spending ranges...")
                    
                    spending_check = """
                    SELECT MIN(total) as min_spending, MAX(total) as max_spending, AVG(total) as avg_spending
                    FROM (
                        SELECT SUM(p.list_price * oi.quantity) as total
                        FROM customers c  
                        JOIN orders o ON c.customer_id = o.customer_id  
                        JOIN order_items oi ON o.order_id = oi.order_id  
                        JOIN products p ON oi.product_id = p.product_id  
                        GROUP BY c.customer_id
                    )
                    """
                    spending_result = execute_query_tool.invoke(spending_check)
                    print(f"Spending ranges: {spending_result}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 4. Problem explanation
        print("\n" + "="*60)
        print("🧠 WHAT WAS WRONG WITH YOUR ORIGINAL QUERY:")
        print("""
        ORIGINAL ISSUE:
        WHERE c.customer_id IN (
            SELECT customer_id 
            FROM orders 
            GROUP BY customer_id 
            HAVING SUM(p.list_price * oi.quantity) > 1000  ❌
        )
        
        PROBLEM: In the subquery, you tried to use 'p.list_price' and 'oi.quantity' 
        but those tables (products, order_items) weren't joined in the subquery.
        
        SOLUTION: Join all necessary tables in the subquery:
        WHERE c.customer_id IN (
            SELECT o2.customer_id 
            FROM orders o2 
            JOIN order_items oi2 ON o2.order_id = oi2.order_id 
            JOIN products p2 ON oi2.product_id = p2.product_id 
            GROUP BY o2.customer_id 
            HAVING SUM(p2.list_price * oi2.quantity) > 1000  ✅
        )
        """)
        
        print("\n🎉 SCRIPT COMPLETED SUCCESSFULLY!")
        print("="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 