from openai import OpenAI
from pydantic import BaseModel
instructions = """
YOU ARE A HELPFUL ASSISTANT THAT STANDARDIZES SEARCH QUERIES SO THAT THEY CAN BE USED IN A SEARCH ENGINE.
You will return a final query that can be used in a search engine.
Always return the final query in english and make sure it can be used properly in a search engine.
The search text that you return needs to be in english.
"""

def standardize_query(query: str) -> str:
    client = OpenAI()
    response = client.responses.create(
        instructions=instructions,
        model='gpt-4.1-mini',
        input=query
    )
    return response.output_text


def guardrail(query: str) -> str:
    """
    Ensures queries are focused on product searches and filters out potentially unsafe or off-topic queries.
    Returns a safe product-focused query or an error message if the query is deemed unsafe.
    """
    client = OpenAI()
    
    guardrail_instructions = """
    YOUR TASK IS TO DETERMINE IF A SEARCH QUERY IS APPROPRIATE FOR PRODUCT SEARCH.
    
    ONLY approve queries that are clearly intended for finding products, items, or shopping-related information.
    
    REJECT queries that:
    - Ask for harmful, illegal, or unethical information
    - Contain hate speech, profanity, or adult content
    - Request personal advice, health information, or political content
    - Attempt to use the search for non-product related purposes
    
    If the query is appropriate for product search, respond with: "APPROVED: [original query]"
    If the query is NOT appropriate, respond with: "REJECTED: This query is not related to product search."
    """


    class Result(BaseModel):
        is_safe: bool

    response = client.responses.parse(
        instructions=guardrail_instructions,
        model='gpt-4.1-mini',
        input=query,
        text_format=Result
    )
    result = response.output_parsed
    return result.is_safe
    if result.is_safe:
        # Extract and return the original query from the approved response
        return query
    else:
        # Return a notification that the query was rejected
        return "Sorry, please enter a product-related search query."