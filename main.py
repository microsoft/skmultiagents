# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import asyncio
import os
import logging
import json
from dotenv import load_dotenv
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.connectors.ai.function_choice_behavior import FunctionChoiceBehavior
from semantic_kernel.contents.utils.author_role import AuthorRole
from semantic_kernel.kernel import Kernel
from azure.core.credentials import AzureKeyCredential
from opentelemetry._logs import set_logger_provider
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import DropAggregation, View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.trace import set_tracer_provider
from azure.monitor.opentelemetry.exporter import (
    AzureMonitorLogExporter,
    AzureMonitorMetricExporter,
    AzureMonitorTraceExporter,
)

import SearchAgent
import ReportAgent
import ValidationAgent

# Load environment variables
load_dotenv()

AppInsights_connection_string = os.environ["AZURE_INSIGHTS_CONNECTION_STRING"]
# Logging Goes here

# Create a resource to represent the service/sample
resource = Resource.create({ResourceAttributes.SERVICE_NAME: "MultiAgentTracing"})

def set_up_logging():
    # Comment appropriate exporter to output monitoring to the local console or Azure App Insights
    exporter = AzureMonitorLogExporter(connection_string=AppInsights_connection_string)
    #exporter = ConsoleLogExporter()

    # Create and set a global logger provider for the application.
    logger_provider = LoggerProvider(resource=resource)
    # Log processors are initialized with an exporter which is responsible
    # for sending the telemetry data to a particular backend.
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    # Sets the global default logger provider
    set_logger_provider(logger_provider)

    # Create a logging handler to write logging records, in OTLP format, to the exporter.
    handler = LoggingHandler()
    # Add filters to the handler to only process records from semantic_kernel.
    handler.addFilter(logging.Filter("semantic_kernel"))
    # Attach the handler to the root logger. `getLogger()` with no arguments returns the root logger.
    # Events from all child loggers will be processed by this handler.
    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def set_up_tracing():
    # Comment appropriate exporter to output monitoring to the local console or Azure App Insights
    exporter = AzureMonitorTraceExporter(connection_string=AppInsights_connection_string)
    #exporter = ConsoleSpanExporter()

    # Initialize a trace provider for the application. This is a factory for creating tracers.
    tracer_provider = TracerProvider(resource=resource)
    # Span processors are initialized with an exporter which is responsible
    # for sending the telemetry data to a particular backend.
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    # Sets the global default tracer provider
    set_tracer_provider(tracer_provider)


def set_up_metrics():
    # Comment appropriate exporter to output monitoring to the local console or Azure App Insights
    exporter = AzureMonitorMetricExporter(connection_string=AppInsights_connection_string)
    #exporter = ConsoleMetricExporter()

    # Initialize a metric provider for the application. This is a factory for creating meters.
    meter_provider = MeterProvider(
        metric_readers=[PeriodicExportingMetricReader(exporter, export_interval_millis=5000)],
        resource=resource,
        views=[
            # Dropping all instrument names except for those starting with "semantic_kernel"
            View(instrument_name="*", aggregation=DropAggregation()),
            View(instrument_name="semantic_kernel*"),
        ],
    )
    # Sets the global default meter provider
    set_meter_provider(meter_provider)


# This must be done before any other telemetry calls
set_up_logging()
set_up_tracing()
set_up_metrics()

# The envionrment variables needed to connect to the gpt-4o model in Azure AI Foundry
deployment_name = os.environ["CHAT_MODEL"]
endpoint = os.environ["CHAT_MODEL_ENDPOINT"]
api_key = os.environ["CHAT_MODEL_API_KEY"]
azure_key_credential = AzureKeyCredential(api_key)

async def main():
    # The Kernel is the main entry point for the Semantic Kernel. It will be used to add services and plugins to the Kernel.
    kernel = Kernel()

    # Add the necessary services and plugins to the Kernel
    # Adding the ReportAgent and SearchAgent plugins will allow the OrchestratorAgent to call the functions in these plugins

    service_id = "orchestrator_agent"
    
    chat_completion_service = AzureChatCompletion(
        service_id=service_id, 
        deployment_name=deployment_name, 
        endpoint=endpoint, 
        api_key=api_key)
    
    kernel.add_service(chat_completion_service)
    kernel.add_plugin(ReportAgent.ReportAgent(), plugin_name="ReportAgent")
    kernel.add_plugin(SearchAgent.SearchAgent(), plugin_name="SearchAgent")
    kernel.add_plugin(ValidationAgent.ValidationAgent(), plugin_name="ValidationAgent")

    settings = kernel.get_prompt_execution_settings_from_service_id(service_id=service_id)
    # Configure the function choice behavior to automatically invoke kernel functions
    settings.function_choice_behavior = FunctionChoiceBehavior.Auto()

    # Create the Orchestrator Agent that will call the Search and Report agents to create the report
    agent = ChatCompletionAgent(
        #service_id="orchestrator_agent",
        kernel=kernel, # The Kernel that contains the services and plugins
        name="OrchestratorAgent",
        instructions=f"""
            You are an agent designed to create detailed reports about health plans. The user will provide the name of a health plan and you will create a detailed report about that health plan. You will also need to validate that the report meets requirements. Call the appropriate functions to help write the report. 
            Do not write the report on your own. Your role is to be an orchestrator who will call the appropriate plugins and functions provided to you. Each plugin that you have available is an agent that can accomplish a specific task. Here are descriptions of the plugins you have available:
            
            - ReportAgent: An agent that writes detailed reports about health plans.
            - SearchAgent: An agent that searches health plan documents.
            - ValidationAgent: An agent that runs validation checks to ensure the generated report meets requirements. It will return 'Pass' if the report meets requirements or 'Fail' if it does not meet requirements.

            Validating that the report meets requirements is critical. If the report does not meet requirements, you must inform the user that the report could not be generated. Do not output a report that does not meet requirements to the user.
            If the report meets requirements, you can output the report to the user. Format your response as a JSON object with two attributes, report_was_generated and content. Here are descriptions of the two attributes:

            - report_was_generated: A boolean value that indicates whether the report was generated. If the report was generated, set this value to True. If the report was not generated, set this value to False.
            - content: A string that contains the report. If the report was generated, this string should contain the detailed report about the health plan. If the report was not generated, this string should contain a message to the user indicating that the report could not be generated.
             
            Here's an example of a JSON object that you can return to the user:
            {{"report_was_generated": false, "content": "The report for the Northwind Standard health plan could not be generated as it did not meet the required validation standards."}}

            Your response must contain only a single valid JSON object. Do not include any additional text, comments, or blank lines before or after it. Use lowercase booleans (true/false) and double quotes for all keys and string values. The JSON object that you generate will be parsed in Python using the json.loads() method. If your output is not a valid JSON object, it will cause an error in the Python code.
            """
    )

    # Start the conversation with the user
    history = ChatHistory()

    is_complete = False
    while not is_complete:
        # Start the logging
        print("Orchestrator Agent is starting...")

        # The user will provide the name of the health plan
        user_input = input("Hello. Please give me the name of a health insurance policy and I will generate a report for you. Type 'exit' to end the conversation: ")
        if not user_input:
            continue
        
        # The user can type 'exit' to end the conversation
        if user_input.lower() == "exit":
            is_complete = True
            break

        # Add the user's message to the chat history
        history.add_message(ChatMessageContent(role=AuthorRole.USER, content=user_input))

        # Invoke the Orchestrator Agent to generate the report based on the user's input
        async for response in agent.invoke(messages=str(history)):
            response_json = json.loads(f"{response.content}")
            report_was_generated = response_json['report_was_generated']
            report_content = response_json['content']

            # Save the report to a file if it was generated
            if report_was_generated:
                report_name = f"{user_input} Report.md"
                with open(f"{report_name}", "w") as f:
                    f.write(report_content)
                    print(f"The report for {user_input} has been generated. Please check the {report_name} file for the report.")
            # Print the requirements failed message if the report was not generated
            elif not report_was_generated:
                print(report_content)
            else:
                print("An unexpected response was received. Please try again") # Print an error message if an unexpected response was received

asyncio.run(main())