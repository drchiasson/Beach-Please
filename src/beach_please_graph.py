#!/usr/bin/env python
from typing import Annotated, Sequence, TypedDict, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.graph.message import add_messages
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode







beach_agent_prompt = "You are a beach day advisor"
beach_agent_data = {}





class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]



#Initialize the agent

tools = []

#TODO pick model and add requisite dependencies
model = "TBD"



#Nodes - List of nodes the AI will utilize

def beach_agent(state: AgentState) -> AgentState:
    """Agent invoker"""

    print("In camping agent")

    system_prompt = SystemMessage(content=beach_agent_prompt + str(beach_agent_data))
    all_messages = [system_prompt] + list(state["messages"])
    response = model.invoke(all_messages) 
    print(f"AI Reponse: {response}")
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

