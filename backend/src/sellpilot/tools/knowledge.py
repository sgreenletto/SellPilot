from pydantic import BaseModel, ConfigDict, Field

from sellpilot.core.enums import ToolRiskLevel
from sellpilot.core.exceptions import ParameterError
from sellpilot.services.rag_service import (
    KNOWLEDGE_NOT_INITIALIZED,
    NO_RELIABLE_ANSWER,
    RAGService,
)
from sellpilot.tools.contracts import RetryPolicy, ToolDefinition, ToolExecutionContext
from sellpilot.tools.registry import ToolRegistry


class KnowledgeToolModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchKnowledgeInput(KnowledgeToolModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    category: str | None = Field(default=None, min_length=1, max_length=64)


class SearchKnowledgeOutput(KnowledgeToolModel):
    answer: str
    sources: list[dict[str, object]]
    answer_mode: str
    no_reliable_source: bool
    knowledge_initialized: bool


async def _search_knowledge(
    payload: SearchKnowledgeInput,
    context: ToolExecutionContext,
) -> SearchKnowledgeOutput:
    if context.session is None or context.settings is None:
        raise ParameterError("knowledge tools require database session and settings")
    result = await RAGService(context.settings, context.session).ask(
        payload.query,
        top_k=payload.top_k,
        category=payload.category,
    )
    return SearchKnowledgeOutput(
        answer=str(result["answer"]),
        sources=list(result["sources"]),
        answer_mode=str(result["answer_mode"]),
        no_reliable_source=result["answer"] in {NO_RELIABLE_ANSWER, KNOWLEDGE_NOT_INITIALIZED},
        knowledge_initialized=bool(result["knowledge_initialized"]),
    )


def build_knowledge_tools() -> tuple[ToolDefinition, ...]:
    return (
        ToolDefinition(
            name="search_knowledge",
            version="1.0.0",
            description="Retrieve bounded knowledge fragments and return a source-grounded answer.",
            input_schema=SearchKnowledgeInput,
            output_schema=SearchKnowledgeOutput,
            risk_level=ToolRiskLevel.READ,
            timeout_seconds=90,
            retry_policy=RetryPolicy(
                max_attempts=1,
                initial_delay_ms=0,
                max_delay_ms=0,
                backoff_multiplier=1,
            ),
            idempotent=True,
            expose_to_mcp=False,
            handler=_search_knowledge,
        ),
    )


def register_knowledge_tools(registry: ToolRegistry) -> None:
    for definition in build_knowledge_tools():
        registry.register(definition)
