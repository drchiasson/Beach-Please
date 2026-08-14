#!/usr/bin/env python
import logging
import sys
from typing import Annotated, Sequence, TypedDict, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_google_genai import ChatGoogleGenerativeAI
from noaa_weather import get_forecasts
from telegram_message_sender import send_bot_message
from tide_predictions_range import get_tide_predictions
from beach_please_prompt import prompt_string
from fog_agent_prompt import fog_prompt
from fog_downloader import get_fog_data
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

load_dotenv()

beach_agent_prompt = prompt_string
fog_agent_prompt = fog_prompt
beach_agent_data = {}
beach_human_message = HumanMessage(content="Marshalls Beach")


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]



#Initialize the agent

#TODO pick model and add requisite dependencies



#Nodes - List of nodes the AI will utilize

def beach_agent(state: AgentState) -> AgentState:
    """Agent invoker"""

    logger.info("In beach agent")

    system_prompt = SystemMessage(content=beach_agent_prompt + str(beach_agent_data))
    
    all_messages = [system_prompt] + [beach_human_message] + list(state["messages"])
    
    response = model.invoke(all_messages) 
    return {"messages": list(state["messages"] + [response])}

def fog_agent(state:AgentState) -> AgentState:
    """Fog Agent Invoker"""
    system_prompt = SystemMessage(content=fog_agent_prompt)
    fog_human_message = HumanMessage(content = "<Fog Data goes here>")
    all_messages = [system_prompt] + [fog_human_message]
    response = fog_model.invoke(all_messages)
    return {"messages": list(state["messages"] + [response])}

def should_continue(state: AgentState) -> AgentState:
    """ Determine if we should continue or end the agent run"""

    logger.info("In should continue")
    
    messages = state["messages"]

    if not messages:
        return "continue"

    last_message = messages[-1]
    #print(last_message)

    if isinstance(last_message.content, str):

        if last_message.content == "fog_data_recieved":
            return "fog_data_ready"

        if last_message.content == "message sent":
            return "end"
    
    return "continue"


#Tools - List of tools the AI will utilize
def forecast_data()->Dict:
    """
        Gets the weather forcast for the beach in question for the current day.

        Args:
            
    """
    logger.info("In get forecast_data")
    return get_forecasts()

def tidal_data(start_date, end_date) -> Dict:
    """ 
        Gets the tidal data for the beach in question for a date range.

        Args:
            start_date: The beginning of the date range you want to get tidal data from.
            end_date: The end of the date range you want to get tidal data from.
    """
    logger.info("In get tidal_data")
    return get_tide_predictions(start_date, end_date)

def telegram_message(message) -> str:
    """
        Sends a telegram message to the telegram channel

        Args:
            message: The message you want to send to the telegram group.
    
    """
    logger.info("In get send telegram message")

    send_bot_message(message)

    return "message sent"

def fog_data(message) -> str:
    """ 
        Gathers the fog data for the current day
    """
    get_fog_data()
    return "fog_data_recieved"

tools = [forecast_data, tidal_data, telegram_message] #, fog_data]
model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite").bind_tools(tools)
fog_model = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")

#Build the graph and the edges
graph = StateGraph(AgentState)

graph.add_node("agent", beach_agent)
graph.add_node("tools", ToolNode(tools))
graph.add_node("fog_agent", fog_agent)

graph.add_edge(START, "agent")
graph.add_conditional_edges(
    "agent",
    tools_condition,
    {"tools": "tools", END: END},
)

graph.add_conditional_edges(
    "tools",
    should_continue,
    {
        "continue": "agent",
       # "fog_data_ready": "fog_agent",
        "end": END
    }
)

graph.add_edge("fog_agent", "agent")

app = graph.compile()

def run_beach_agent():
    logger.info("==Beach Please Agent==")
    state = {"messages": []}
    try:
        for step_count, step in enumerate(app.stream(state, stream_mode="values"), start=1):
            logger.debug("Step: %s", step_count)
    except Exception:
        logger.exception("Beach agent run failed")
        try:
            send_bot_message("Beach Please run failed - check logs.")
        except Exception:
            logger.exception("Failed to send failure notification")
        raise

if __name__ == "__main__":
    run_beach_agent()

