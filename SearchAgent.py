# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
from semantic_kernel.functions import kernel_function
from dotenv import load_dotenv
from azure.ai.agents.models import AzureAISearchTool, MessageRole
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

load_dotenv()

class SearchAgent:
    """
    A class to represent the Search Agent.
    """
    @kernel_function(description='An agent that searches health plan documents.')
    def search_plan_docs(self, plan_name:str) -> str:
        """
        Creates an Azure AI Agent that searches an Azure AI Search index for information about a health plan.

        Parameters:
        plan_name (str): The name of the health plan to search for.

        Returns:
        last_msg (json): The last message from the agent, which contains the information about the health plan.

        """
        print("Calling SearchAgent...")

        # Connecting to our Azure AI Foundry project, which will allow us to use the deployed gpt-4o model for our agent
        
        project_client = AIProjectClient(
            os.environ["AIPROJECT_ENDPOINT"],
            DefaultAzureCredential()
            )

        #agents_client = AgentsClient(
        #    os.environ["AIPROJECT_ENDPOINT"],
        #    DefaultAzureCredential()
        #    )
        
        # Iterate through the connections in your project and get the connection ID of the Azure AI Search connection.
        conn_list = project_client.connections.list()
        conn_id = ""
        for conn in conn_list:
           #print(conn.type)
           if conn.type == "CognitiveSearch":
               conn_id = conn.id
        # Connect to your Azure AI Search index
        ai_search = AzureAISearchTool(index_connection_id=conn_id, index_name=os.environ["AISEARCH_INDEX_NAME"])

        # Create an agent that will be used to search for health plan information
        search_agent = project_client.agents.create_agent(
            model=os.environ["CHAT_MODEL"],
            name="search-agent",
            instructions="You are a helpful agent that is an expert at searching health plan documents.", # System prompt for the agent
            tools=ai_search.definitions,
            tool_resources=ai_search.resources
        ) 

        # Create a thread which is a conversation session between an agent and a user. 
        thread = project_client.agents.threads.create()

        # Create a message in the thread with the user asking for information about a specific health plan
        message = project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Tell me about the {plan_name} plan.", # The user's message
        )

        # Run the agent to process tne message in the thread
        run = project_client.agents.runs.create_and_process(thread_id=thread.id, agent_id=search_agent.id)

        # Check if the run was successful
        if run.status == "failed":
            print(f"Run failed: {run.last_error}")

        # Delete the agent when it's done running
        project_client.agents.delete_agent(search_agent.id)

        # Get the last message from the thread
        last_msg = project_client.agents.messages.get_last_message_text_by_role(thread_id=thread.id,role=MessageRole.AGENT)
      
        print("SearchAgent completed successfully.")

        return str(last_msg)
