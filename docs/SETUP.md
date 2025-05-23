#### Initial Setup
##### Step 1: Creating the project in AI Foundry

1. Login to Azure AI Foundry at [https://ai.azure.com](https://ai.azure.com)
2. Click on the "Create new" button on the top-right of the screen
3. Give your project a name and expand the "Advanced Options". Verify the Subscription, Resource Group (create a new one to avoid conflicts with previous library versions), Azure AI Foundry resource, and the Region.

![Azure AI Foundry portal screenshot Create Project](https://github.com/commercial-software-engineering/skmultiagents/blob/main/docs/AzureAIFoundryCreateProject.jpg)

* Notice that Azure AI Foundry projects can now be created without the need to instantiate an Azure AI Hub. Hub-less projects (the ones created from the Foundry portal by default) are assigned to an Azure AI Foundry resource that can be found in the Azure Portal Resources.

##### Step 2: Deploy gpt-41 model for your Foundry project

The agents in this project will require access to a Large Language Model (LLM). The next step is to deploy one of them for chat completion purposes. Notice that you can deploy multiple models and decide which one each agent will consume depending on their tasks.

1. In the AI Foundry project, under "My assets" section, click on the 'Models + endpoints'.
2. Click on Deploy model and Deploy base model.
3. Select gpt-4.1 (chat completion) and then press Confirm.
4. Select a Deployment name, and then click on Customize. Set the model version to the latest one and the Tokens per Minute Rate Limit to 200k. You can also set the Content Filter. Leave the Connected AI Resource as it is.

##### Step 3: Create a storage account

1. Login to the Azure Portal under the same subscription where the Azure AI Foundry project was created. 
2. Under the same resource group used to create the Azure AI Foundry project, add a Storage account

![Azure Portal Create Storage Account](https://github.com/commercial-software-engineering/skmultiagents/blob/main/docs/AzurePortalCreateStorageAcct.jpg){data-source-line=16}

* Notice that a default Azure Storage Account for the Foundry project is not automatically created for you anymore.

3. Once the storage account has been created, navigate to it and Expand the "Data Storage" in the side menu. Click on "Containers"

![Azure Portal Create Storage Account Container](https://github.com/commercial-software-engineering/skmultiagents/blob/main/docs/AzurePortalCreateContainer.jpg){data-source-line=16}

4. Create a new container named "healthplan"

5. Click into the new container and upload the two PDF documents in this repository (they can be located under the "data" folder)

##### Step 4: Create an Azure AI Search service
##### Step 4a: Deploy Text Embedding Model for Search Indexing

The import and vectorize wizard in Azure AI Search does not yet support text embedding models within the AI Foundry project. Because of this, it is required to create an Azure OpenAI service and deploy a text embedding model there. This text embedding model will be used later to vectorize the health plan documents.

1. Navigate to the resource group that was created upon setting the AI Foundry Project.
2. Deploy an Azure OpenAI Service resource in this resource group.
3. In the newly created Azure OpenAI service, click Go to Azure AI Foundry portal. Notice that this is outside of the Foundry project.
4. Under the "Shared Resources" section, click on Deployments.
5. Click on Deploy model and then Deploy base model. Select text-embedding-3-large and deploy it.

##### Step 4b: Create and Azure AI Search resource and vectorize documents

1. Navigate to the resource group that was created upon setting the AI Foundry Project.
2. Create an Azure AI Search Service resource in this resource group.
3. Once in the creation wizard, under "Basic" enter a Service name. Change the Pricing tier to "Free". This is more than enough for the demo.
4. Click on "Review + Create". Review the information and click on "Create".
5. Once created, navigate to the Azure AI Search resource and under Settings in the left menu, select Keys.
2. Under API Access control select Both.
3. Navigate to Identity under Settings. Under System-assigned set the Status to On and save.

##### Step 4c: Assign permissions to the Azure AI Search

1. Navigate to the Storage Account for the project, created on Step #3.
2. Select Access control (IAM).
3. Select Add (top menu), and then select Add role assignment.
4. Under Job function roles, select Storage Blob Data Reader and then select Next.
5. Under Members, select Managed identity, and then select Members.
6. Filter by subscription and resource type (search services), and then select the managed identity of your Azure AI search service created on Step 4b.
7. Select Review + assign.

##### Step 4d: Index documents with Azure AI Search

1. Navigate to the Azure AI Search Service.
2. On the Overview page, select Import and vectorize data.
3. On Set up your data connection, select Azure Blob Storage. Select RAG.
4. Specify your subscription, storage account, and the container that contains your healthplans PDF documents (created in Step #3).
5. Make sure "Authenticate using managed identity" is checked and the Managed identity type is set to System-assigned.
6. On the Vectorize your text page, select the Deployment Model by clicking on the drop down menu. It should show the one it was created in Step #4a (text-embedding-3-large).
6. On the Vectorize and enrich your images page, leave the boxes unchecked.
7. On the Advanced setting page, don't change anything and click Next.
8. Click on Create. This will start the document indexing process which will vectorize your documents and create an index.

##### Step 5: Create an App Insights resource connected to the project

1. Navigate to the resource group that was created upon setting the AI Foundry Project.
2. Create an Azure Application Insights service in this resource group.
3. Choose a name, region, and click on "Review + Create"
4. Review the options and click on "Create"

#### Environment variables

Needed to log GenAI metrics in App Insights

*SEMANTICKERNEL_EXPERIMENTAL_GENAI_ENABLE_OTEL_DIAGNOSTICS_SENSITIVE = true*

Azure App Insigths connection string for telemetry.Find it under the Application Insights Resource created in Step #5

*AZURE_INSIGHTS_CONNECTION_STRING = ""*

AI Search Index Name. The one used in Step #4d

*AISEARCH_INDEX_NAME = ""*

The AI Foundry Project endpoint, found in the Foundry Project Overview page

*AIPROJECT_ENDPOINT = ""*

AI Foundry project chat model created in Step #2

*CHAT_MODEL_ENDPOINT = ""*

*CHAT_MODEL_API_KEY =* 

*CHAT_MODEL =* 
