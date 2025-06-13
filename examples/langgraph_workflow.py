"""
Example LangGraph workflow.

This module demonstrates how to use LangGraph to create a workflow with multiple steps.
The workflow implements a natural language to SQL query pipeline with the following steps:
1. Extract entities from the natural language query
2. Retrieve database schema
3. Generate SQL query
4. Execute the query
5. Format the response
6. Handle any errors that occur

The workflow uses LangGraph's StateGraph to manage the flow between steps and handle state.
Each step is implemented as an async function that takes and returns the workflow state.
"""
import os
from typing import Dict, Any, List, Tuple, TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import StateGraph, END


# Define the state that will be passed between workflow steps
class WorkflowState(TypedDict):
    """
    State for the workflow.
    
    Attributes:
        query (str): The original natural language query
        extracted_entities (Dict[str, Any]): Entities extracted from the query (e.g., table names, filters)
        database_schema (str): The database schema in a readable format
        sql_query (str): The generated SQL query
        query_result (List[Dict[str, Any]]): Results from executing the SQL query
        final_response (str): The formatted response to return to the user
        error (str): Any error message if something goes wrong
    """
    query: str
    extracted_entities: Dict[str, Any]
    database_schema: str
    sql_query: str
    query_result: List[Dict[str, Any]]
    final_response: str
    error: str


# Define the workflow steps
async def extract_entities(state: WorkflowState) -> WorkflowState:
    """
    Extract entities from the query.
    
    This step analyzes the natural language query to identify:
    - Which table to query (e.g., users, products)
    - Any specific filters or conditions
    - Entity names or values to search for
    
    In a real implementation, this would use an LLM to extract entities.
    Here we use a simple rule-based approach for demonstration.
    
    Args:
        state (WorkflowState): Current workflow state containing the query
        
    Returns:
        WorkflowState: Updated state with extracted entities
    """
    print("Extracting entities...")
    
    # In a real implementation, this would use an LLM to extract entities
    query = state["query"]
    
    # Simulated entity extraction
    entities = {}
    if "user" in query.lower():
        entities["table"] = "users"
        if "john" in query.lower():
            entities["name"] = "John"
    elif "product" in query.lower():
        entities["table"] = "products"
        if "electronics" in query.lower():
            entities["category"] = "Electronics"
    
    new_state = state.copy()
    new_state["extracted_entities"] = entities
    
    return new_state


async def get_database_schema(state: WorkflowState) -> WorkflowState:
    """
    Get the database schema.
    
    This step retrieves the database schema to understand:
    - Available tables
    - Column names and types
    - Primary keys and relationships
    
    In a real implementation, this would query the database for its schema.
    Here we use a simulated schema for demonstration.
    
    Args:
        state (WorkflowState): Current workflow state
        
    Returns:
        WorkflowState: Updated state with database schema
    """
    print("Getting database schema...")
    
    # In a real implementation, this would query the database for its schema
    new_state = state.copy()
    
    # Simulated schema
    new_state["database_schema"] = """
    Table: users
    - user_id (INTEGER, PK)
    - username (TEXT)
    - email (TEXT)
    - first_name (TEXT)
    - last_name (TEXT)
    - created_at (TEXT)
    
    Table: products
    - product_id (INTEGER, PK)
    - name (TEXT)
    - description (TEXT)
    - price (REAL)
    - category (TEXT)
    - in_stock (BOOLEAN)
    """
    
    return new_state


async def generate_sql(state: WorkflowState) -> WorkflowState:
    """
    Generate SQL from the query and entities.
    
    This step uses an LLM to convert the natural language query and extracted entities
    into a valid SQL query. The LLM is provided with:
    - The database schema
    - The original query
    - Extracted entities
    
    Args:
        state (WorkflowState): Current workflow state containing query, entities, and schema
        
    Returns:
        WorkflowState: Updated state with generated SQL query
    """
    print("Generating SQL...")
    
    # Use LLM to generate SQL
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an expert SQL assistant. Convert the natural language query to SQL based on the schema.
        Return ONLY the SQL query without any explanation or additional text.
        
        Schema:
        {schema}
        """),
        ("human", """
        Query: {query}
        Extracted entities: {entities}
        """)
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    sql = await chain.ainvoke({
        "schema": state["database_schema"],
        "query": state["query"],
        "entities": state["extracted_entities"]
    })
    
    new_state = state.copy()
    new_state["sql_query"] = sql
    
    return new_state


async def execute_query(state: WorkflowState) -> WorkflowState:
    """
    Execute the SQL query.
    
    This step runs the generated SQL query against the database and retrieves the results.
    In a real implementation, this would:
    1. Connect to the database
    2. Execute the query
    3. Handle any database errors
    4. Return the results
    
    Here we use simulated results for demonstration.
    
    Args:
        state (WorkflowState): Current workflow state containing the SQL query
        
    Returns:
        WorkflowState: Updated state with query results
    """
    print("Executing query:", state["sql_query"])
    
    # In a real implementation, this would execute the SQL against a database
    new_state = state.copy()
    
    # Simulated query results
    if "users" in state["sql_query"].lower():
        new_state["query_result"] = [
            {"user_id": 1, "username": "jsmith", "email": "john.smith@example.com", "first_name": "John", "last_name": "Smith"},
            {"user_id": 2, "username": "ajones", "email": "alice.jones@example.com", "first_name": "Alice", "last_name": "Jones"}
        ]
    elif "products" in state["sql_query"].lower() and "electronics" in state["sql_query"].lower():
        new_state["query_result"] = [
            {"product_id": 1, "name": "Laptop", "price": 1299.99, "category": "Electronics"},
            {"product_id": 2, "name": "Smartphone", "price": 799.99, "category": "Electronics"},
            {"product_id": 9, "name": "Tablet", "price": 399.99, "category": "Electronics"}
        ]
    else:
        new_state["query_result"] = []
    
    return new_state


async def format_response(state: WorkflowState) -> WorkflowState:
    """
    Format the final response.
    
    This step uses an LLM to convert the query results into a natural language response.
    The LLM is provided with:
    - The original query
    - The SQL query that was executed
    - The query results
    
    The goal is to make the response conversational and helpful.
    
    Args:
        state (WorkflowState): Current workflow state containing query results
        
    Returns:
        WorkflowState: Updated state with formatted response
    """
    print("Formatting response...")
    
    # Use LLM to format the response
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are a helpful assistant. Format the query results into a natural language response.
        Make the response conversational and helpful.
        """),
        ("human", """
        Original query: {query}
        SQL query: {sql}
        Query results: {results}
        """)
    ])
    
    chain = prompt | llm | StrOutputParser()
    
    response = await chain.ainvoke({
        "query": state["query"],
        "sql": state["sql_query"],
        "results": state["query_result"]
    })
    
    new_state = state.copy()
    new_state["final_response"] = response
    
    return new_state


async def handle_error(state: WorkflowState) -> WorkflowState:
    """
    Handle errors in the workflow.
    
    This step is called when an error occurs in any of the workflow steps.
    It formats the error message into a user-friendly response.
    
    Args:
        state (WorkflowState): Current workflow state containing the error
        
    Returns:
        WorkflowState: Updated state with error response
    """
    print("Handling error...")
    
    new_state = state.copy()
    new_state["final_response"] = f"An error occurred: {state['error']}"
    
    return new_state


# Create the workflow
def create_workflow():
    """
    Create the workflow graph.
    
    This function sets up the LangGraph workflow by:
    1. Creating a StateGraph with our WorkflowState
    2. Adding nodes for each step in the workflow
    3. Defining the edges between steps
    4. Setting up error handling
    5. Compiling the graph
    
    The workflow follows this sequence:
    extract_entities -> get_database_schema -> generate_sql -> execute_query -> format_response
    
    Error handling is added at each step to catch and handle any errors that occur.
    
    Returns:
        Compiled workflow graph ready to be executed
    """
    # Create the graph
    workflow = StateGraph(WorkflowState)
    
    # Add nodes for each step in the workflow
    workflow.add_node("extract_entities", extract_entities)
    workflow.add_node("get_database_schema", get_database_schema)
    workflow.add_node("generate_sql", generate_sql)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("format_response", format_response)
    workflow.add_node("handle_error", handle_error)
    
    # Define the main flow of the workflow
    workflow.set_entry_point("extract_entities")
    workflow.add_edge("extract_entities", "get_database_schema")
    workflow.add_edge("get_database_schema", "generate_sql")
    workflow.add_edge("generate_sql", "execute_query")
    workflow.add_edge("execute_query", "format_response")
    workflow.add_edge("format_response", END)
    workflow.add_edge("handle_error", END)
    
    # Define conditional edges for error handling
    def should_handle_error(state: WorkflowState) -> str:
        """
        Check if there's an error in the state.
        
        Args:
            state (WorkflowState): Current workflow state
            
        Returns:
            str: "handle_error" if there's an error, "default" otherwise
        """
        if state.get("error"):
            return "handle_error"
        return "default"
    
    # Add error handling for each step
    workflow.add_conditional_edges("extract_entities", should_handle_error, {
        "handle_error": "handle_error",
        "default": "get_database_schema"
    })
    
    workflow.add_conditional_edges("get_database_schema", should_handle_error, {
        "handle_error": "handle_error",
        "default": "generate_sql"
    })
    
    workflow.add_conditional_edges("generate_sql", should_handle_error, {
        "handle_error": "handle_error",
        "default": "execute_query"
    })
    
    workflow.add_conditional_edges("execute_query", should_handle_error, {
        "handle_error": "handle_error",
        "default": "format_response"
    })
    
    # Compile the graph
    return workflow.compile()


async def run_workflow(query: str) -> str:
    """
    Run the workflow with a query.
    
    Args:
        query: The natural language query
        
    Returns:
        The formatted response
    """
    # Create the workflow
    workflow = create_workflow()
    
    # Initialize the state
    initial_state = {
        "query": query,
        "extracted_entities": {},
        "database_schema": "",
        "sql_query": "",
        "query_result": [],
        "final_response": "",
        "error": ""
    }
    
    # Execute the workflow
    try:
        final_state = await workflow.ainvoke(initial_state)
        return final_state["final_response"]
    except Exception as e:
        return f"Workflow execution failed: {str(e)}"


async def main():
    """
    Run example queries through the workflow.
    """
    queries = [
        "Find all users with the name John",
        "What electronics products do we have?",
        "Show me all products that cost less than $100"
    ]
    
    for query in queries:
        print("\n" + "=" * 50)
        print(f"Query: {query}")
        print("=" * 50)
        
        response = await run_workflow(query)
        print("\nResponse:")
        print(response)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 