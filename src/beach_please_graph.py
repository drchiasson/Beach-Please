#!/usr/bin/env python
from typing import Annotated, Sequence, TypedDict, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_google_genai import ChatGoogleGenerativeAI
from noaa_weather import get_forecasts
from telegram_message_sender import send_bot_message




beach_agent_prompt = "You are a beach day planner agent. We need to find out which days are good to go to the beach. Call the tools needed to determine the best day to go to the beach and then choose which days are best to go to the beach"
beach_human_message = HumanMessage(content="Marshalls Beach")
beach_agent_data = {}





class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]



#Initialize the agent



#TODO pick model and add requisite dependencies
model = ChatGoogleGenerativeAI(model="gemini-3.5-flash")


#Nodes - List of nodes the AI will utilize

def beach_agent(state: AgentState) -> AgentState:
    """Agent invoker"""

    print("In beach agent")

    system_prompt = SystemMessage(content=beach_agent_prompt + str(beach_agent_data))
    
    all_messages = [system_prompt] + [beach_human_message] + list(state["messages"])
    
    response = model.invoke(all_messages) 
    return {"messages": list(state["messages"] + [response])}

def should_continue(state: AgentState) -> AgentState:
    """ Determine if we should continue or end the agent run"""

    print("In should continue")
    
    messages = state["messages"]

    if not messages:
        return "continue"

    last_message = messages[-1]
    print("Last Message:" + last_message.content)

    if last_message.content == "message sent":
        return "end"
    
    return "continue"


#Tools - List of tools the AI will utilize
def weather_data()->Dict:
    """
        Gets the weather forcast for the beach in question for the current day.

        Args:
            
    """
    return get_forecasts()


def telegram_message(message) -> str:
    """
        Sends a telegram message to the telegram channel

        Args:
            message: The message you want to send to the telegram group.
    
    """
    send_bot_message(message)

    return "message sent"



tools = [weather_data, telegram_message]

#Build the graph and the edges
graph = StateGraph(AgentState)

graph.add_node("agent", beach_agent)
graph.add_node("tools", ToolNode(tools))

graph.add_edge(START, "agent")
graph.add_edge("agent", "tools")

graph.add_conditional_edges(
    "tools",
    should_continue,
    {
        "continue": "agent",
        "end": END
    }
)

app = graph.compile()

def run_beach_agent():
    print("==Beach Please Agent==")
    x=0
    state = {"messages":[]}
    for step in app.stream(state, stream_mode ="values"):
        x+=1
        print("Step: ", x)

run_beach_agent()

