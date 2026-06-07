from pydantic import BaseModel

from flywheel.core.agent import SingleCallAgent
from flywheel.libraries.llm_gateway import FakeLLMGateway


class Result(BaseModel):
    value: str = ""


def test_single_call_agent_builds_prompt_and_returns_schema() -> None:
    seen_prompts: list[str] = []

    def builder(inputs) -> str:
        prompt = f"do:{inputs['task']}"
        seen_prompts.append(prompt)
        return prompt

    gw = FakeLLMGateway()
    gw.register("Result", lambda prompt: {"value": prompt})
    agent = SingleCallAgent(gw, builder)

    out, completion = agent.run({"task": "scan"}, Result)

    assert seen_prompts == ["do:scan"]
    assert out.value == "do:scan"
    assert completion.model == "fake/echo-1"
