from typing import Dict, List, Any, TypedDict
from langgraph.graph import StateGraph, END
from utils.query_helpers import FHIRQueryHelper, openrouter_chat

# Define the state type for our graph
class OutreachState(TypedDict):
    messages: List[Dict[str, Any]]
    patient_data: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    outreach_drafts: Dict[str, str]

def create_outreach_agent() -> StateGraph:
    """Create an outreach agent that generates personalized emails."""
    
    def generate_outreach(state: Dict[str, Any]) -> Dict[str, Any]:
        outreach_drafts = {}
        
        for patient_name, assessment in state["risk_assessment"].items():
            print(f"[DEBUG] Generating outreach for {patient_name} with risk level {assessment['risk_level']}")
            # Generate outreach email using OpenRouter
            prompt = f"""Generate a personalized outreach email for {patient_name}:
            Risk Level: {assessment['risk_level']}
            Assessment: {assessment['explanation']}
            
            Create a professional, empathetic email that:
            1. Addresses their specific health concerns
            2. Suggests next steps
            3. Maintains a supportive tone"""
            print(f"[DEBUG] Using openrouter_chat for {patient_name}")
            email = openrouter_chat([
                {"role": "user", "content": prompt}
            ])
            print(f"[DEBUG] openrouter_chat response for {patient_name}: {email}")
            outreach_drafts[patient_name] = email
        
        state["outreach_drafts"] = outreach_drafts
        return state
    
    # Create the graph
    workflow = StateGraph(OutreachState)
    
    # Add the outreach generation node
    workflow.add_node("generate", generate_outreach)
    
    # Set the entry point
    workflow.set_entry_point("generate")
    
    # Set the exit point
    workflow.add_edge("generate", END)
    
    # Compile the graph
    return workflow.compile()

if __name__ == "__main__":
    import json
    with open("data/patients.json", "r") as f:
        patient_data = json.load(f)
    agent = create_outreach_agent()
    result = agent.invoke({
        "messages": [],
        "patient_data": patient_data,
        "risk_assessment": {
            "John Smith": {
                "risk_level": "HIGH",
                "explanation": "Patient has severe diabetes with multiple risk factors",
                "recommended_actions": ["Schedule follow-up appointment", "Review medication"]
            }
        },
        "outreach_drafts": {}
    })
    print(result["outreach_drafts"]) 