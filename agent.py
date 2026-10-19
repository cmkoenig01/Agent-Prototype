# loads the model, defines one drug rule + a lookup tool, runs the tool-call loop

import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from dataclasses import dataclass

# load qwen3-4b onto the mac gpu (mps), else cpu
MODEL_NAME = "Qwen/Qwen3-4B-Instruct-2507"
if torch.backends.mps.is_available():
    DEVICE = "mps"
else:
    DEVICE = "cpu"

print("loading model:", MODEL_NAME, "on", DEVICE)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, dtype=torch.bfloat16).to(DEVICE)
print("model loaded.")

# --- knowledge: hand-written drug safety rules ---
@dataclass
class Guideline:
    drug: str                      # lookup key
    gene: str                      # allele to screen for
    higher_risk_populations: list  # ancestries where it's more common
    risk_if_positive: str          # harm if the patient carries it
    verdict_if_positive: str       # decision when positive
    source: str                    # citation


# our rules, one for now
GUIDELINES = [
    Guideline(
        drug="carbamazepine",
        gene="HLA-B*15:02",
        higher_risk_populations=["Han Chinese", "Thai", "Southeast Asian"],
        risk_if_positive="Stevens-Johnson syndrome (severe skin reaction)",
        verdict_if_positive="avoid",
        source="CPIC HLA-B / carbamazepine (2017)",
    ),
]


# the real tool body: drug name -> matching Guideline, or None
def lookup_guideline(drug):
    for guideline in GUIDELINES:
        if guideline.drug == drug:
            return guideline
    return None

# send messages to the model, return its reply text
# messages: [{"role": "user", "content": "..."}]  tools: optional tool defs the model may call
def generate(messages, tools=None, max_new_tokens=512):
    # build the prompt text qwen3 expects (messages + any tools)
    prompt_text = tokenizer.apply_chat_template(
        messages,
        tools=tools,
        tokenize=False,
        add_generation_prompt=True,
    )
    # tokens on device -> generate -> decode only the new tokens
    inputs = tokenizer(prompt_text, return_tensors="pt").to(DEVICE)
    output_ids = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        do_sample=False,
    )
    new_tokens = output_ids[0][inputs["input_ids"].shape[1]:]
    reply = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return reply

# definition: describes lookup_guideline to the model (name must match the real function)
LOOKUP_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_guideline",
        "description": (
            "look up a drug's prescribing-safety guideline. use before deciding whether "
            "a patient can take a drug. returns the gene to screen for, higher-risk "
            "populations, the risk if positive, the recommended verdict, and the source."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "drug": {"type": "string", "description": "drug name, e.g. 'carbamazepine'"},
            },
            "required": ["drug"],
        },
    },
}


# runner: model asks for a tool by name + args; we run the real function, return text
def run_tool(name, args):
    if name == "lookup_guideline":
        guideline = lookup_guideline(args["drug"])
        if guideline is None:
            return "no guideline found for " + args["drug"]
        # format the dataclass into readable text for the model
        return (
            "drug: " + guideline.drug + "\n"
            "gene to screen: " + guideline.gene + "\n"
            "higher-risk populations: " + ", ".join(guideline.higher_risk_populations) + "\n"
            "risk if positive: " + guideline.risk_if_positive + "\n"
            "verdict if positive: " + guideline.verdict_if_positive + "\n"
            "source: " + guideline.source
        )
    return "unknown tool: " + name

# --- the agentic loop ---

# system prompt: the model's job + how to treat ancestry
SYSTEM = (
    "you are a prescription-safety screening assistant. given a patient and a drug, "
    "decide if the patient is clear to take it. always call lookup_guideline to get the "
    "drug's rule; never guess it. treat ancestry as a screening prior only: it tells you "
    "which gene to check, it does not by itself decide the verdict. if the patient's "
    "genotype is unknown, recommend screening. end with a short verdict (suitable / screen "
    "first / avoid) and a one-line reason that cites the source."
)


# find a <tool_call>...</tool_call> in the output, return (name, args) or (None, None)
def parse_tool_call(text):
    start = text.find("<tool_call>")
    end = text.find("</tool_call>")
    if start == -1 or end == -1:
        return None, None
    raw = text[start + len("<tool_call>"):end].strip()
    call = json.loads(raw)
    return call["name"], call["arguments"]


# run one patient question through the model + tool loop
def ask(question):
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": question},
    ]
    # loop up to 6 rounds so a stuck model can't spin forever
    for step in range(6):
        reply = generate(messages, tools=[LOOKUP_TOOL])
        name, args = parse_tool_call(reply)
        # no tool call -> this is the final answer
        if name is None:
            return reply
        # model asked for a tool: record the call, run it, hand back the result
        print("tool call:", name, args)
        messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": [{"type": "function", "function": {"name": name, "arguments": args}}],
        })
        result = run_tool(name, args)
        messages.append({"role": "tool", "name": name, "content": result})
    return reply


# test run
if __name__ == "__main__":
    question = (
        "patient: 34-year-old woman, han chinese ancestry, hla genotype not tested. "
        "she is being considered for glp-1. is she clear to take it?"
    )
    print("\n--- answer ---")
    print(ask(question))




