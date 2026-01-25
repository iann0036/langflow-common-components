from __future__ import annotations

# pyright: reportCallIssue=false
from typing import Any, cast
from lfx.custom.custom_component.component import Component
from lfx.io import HandleInput, DropdownInput, Output
from lfx.schema import (
    Message,
    Data,
    DataFrame
)
from lfx.field_typing import (
    AgentExecutor,
    BaseChatMemory,
    BaseChatModel,
    BaseDocumentCompressor,
    BaseLanguageModel,
    BaseLLM,
    BaseLoader,
    BaseMemory,
    BaseOutputParser,
    BasePromptTemplate,
    BaseRetriever,
    Callable,
    Chain,
    ChatPromptTemplate,
    Code,
    Document,
    Embeddings,
    #LanguageModel,
    NestedDict,
    Object,
    PromptTemplate,
    #Retriever,
    Text,
    TextSplitter,
    Tool,
    VectorStore,
) # https://github.com/langflow-ai/langflow/blob/main/src/lfx/src/lfx/field_typing/constants.py

ALL_INPUT_TYPES = [
    "AgentExecutor",
    "BaseChatMemory",
    "BaseChatModel",
    "BaseDocumentCompressor",
    "BaseLanguageModel",
    "BaseLLM",
    "BaseLoader",
    "BaseMemory",
    "BaseOutputParser",
    "BasePromptTemplate",
    "BaseRetriever",
    "Callable",
    "Chain",
    "ChatPromptTemplate",
    "Code",
    "Data",
    "DataFrame",
    "Document",
    "Embeddings",
    "Message",
    "NestedDict",
    "Object",
    "PromptTemplate",
    "Text",
    "TextSplitter",
    "Tool",
    "VectorStore"
]

# Mapping of type names to their actual type objects
TYPE_MAP = {
    "AgentExecutor": AgentExecutor,
    "BaseChatMemory": BaseChatMemory,
    "BaseChatModel": BaseChatModel,
    "BaseDocumentCompressor": BaseDocumentCompressor,
    "BaseLanguageModel": BaseLanguageModel,
    "BaseLLM": BaseLLM,
    "BaseLoader": BaseLoader,
    "BaseMemory": BaseMemory,
    "BaseOutputParser": BaseOutputParser,
    "BasePromptTemplate": BasePromptTemplate,
    "BaseRetriever": BaseRetriever,
    "Callable": Callable,
    "Chain": Chain,
    "ChatPromptTemplate": ChatPromptTemplate,
    "Code": Code,
    "Data": Data,
    "DataFrame": DataFrame,
    "Document": Document,
    "Embeddings": Embeddings,
    "Message": Message,
    "NestedDict": NestedDict,
    "Object": Object,
    "PromptTemplate": PromptTemplate,
    "Text": Text,
    "TextSplitter": TextSplitter,
    "Tool": Tool,
    "VectorStore": VectorStore,
}


class PassthroughDependency(Component):
    display_name = "Passthrough with dependency"
    description = "Sends an input directly to the output only when all dependent ignored inputs are received. Additional ignored inputs can be added from Controls."
    documentation: str = "https://github.com/iann0036/langflow-common-components"
    icon = "arrow-right" # https://lucide.dev/icons/
    name = "PassthroughDependency"

    inputs: list[Any] = [
        HandleInput(
            name="original_input",
            display_name="Original Input",
            input_types=ALL_INPUT_TYPES,
            info="The input which will be preserved and passed through to the output.",
            required=True,
        ),
        HandleInput(
            name="ignored_input_1",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
        ),
        HandleInput(
            name="ignored_input_2",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_3",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_4",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_5",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_6",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_7",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_8",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        HandleInput(
            name="ignored_input_9",
            display_name="Ignored Input",
            input_types=ALL_INPUT_TYPES,
            info="An input which is ignored.",
            advanced=True,
        ),
        DropdownInput(
            name="original_input_type",
            display_name="Input Type",
            options=ALL_INPUT_TYPES,
            info="Select the original input data type.",
            real_time_refresh=True,
            value="Message"
        ),
    ]

    outputs = [
        Output(display_name="Original Input", name="output", method="passthrough_input"),
    ]

    def update_outputs(self, frontend_node: dict, field_name: str, field_value: Any) -> dict:
        """Dynamically show only the relevant output based on the selected output type."""
        if field_name == "original_input_type" and field_value in ALL_INPUT_TYPES:
            frontend_node["outputs"] = [
                Output(
                    display_name="Original Input",
                    name="output",
                    method=f"passthrough_input_{field_value.lower()}",
                ).to_dict()
            ]
        return frontend_node

    def passthrough_input(self) -> Any: # Default passthrough method
        return self.original_input

    def passthrough_input_agentexecutor(self) -> AgentExecutor:
        return self.original_input
    
    def passthrough_input_basechatmemory(self) -> BaseChatMemory:
        return self.original_input
    
    def passthrough_input_basechatmodel(self) -> BaseChatModel:
        return self.original_input
    
    def passthrough_input_basedocumentcompressor(self) -> BaseDocumentCompressor:
        return self.original_input
    
    def passthrough_input_baselanguagemodel(self) -> BaseLanguageModel:
        return self.original_input
    
    def passthrough_input_basellm(self) -> BaseLLM:
        return self.original_input
    
    def passthrough_input_baseloader(self) -> BaseLoader:
        return self.original_input
    
    def passthrough_input_basememory(self) -> BaseMemory:
        return self.original_input
    
    def passthrough_input_baseoutputparser(self) -> BaseOutputParser:
        return self.original_input
    
    def passthrough_input_baseprompttemplate(self) -> BasePromptTemplate:
        return self.original_input
    
    def passthrough_input_baseretriever(self) -> BaseRetriever:
        return self.original_input
    
    def passthrough_input_callable(self) -> Callable:
        return self.original_input
    
    def passthrough_input_chain(self) -> Chain:
        return self.original_input
    
    def passthrough_input_chatprompttemplate(self) -> ChatPromptTemplate:
        return self.original_input
    
    def passthrough_input_code(self) -> Code:
        return self.original_input
    
    def passthrough_input_data(self) -> Data:
        return self.original_input
    
    def passthrough_input_dataframe(self) -> DataFrame:
        return self.original_input
    
    def passthrough_input_document(self) -> Document:
        return self.original_input
    
    def passthrough_input_embeddings(self) -> Embeddings:
        return self.original_input
    
    def passthrough_input_message(self) -> Message:
        return self.original_input
    
    def passthrough_input_nesteddict(self) -> NestedDict:
        return self.original_input
    
    def passthrough_input_object(self) -> Object:
        return self.original_input
    
    def passthrough_input_prompttemplate(self) -> PromptTemplate:
        return self.original_input
    
    def passthrough_input_text(self) -> Text:
        return self.original_input
    
    def passthrough_input_textsplitter(self) -> TextSplitter:
        return self.original_input
    
    def passthrough_input_tool(self) -> Tool:
        return self.original_input
    
    def passthrough_input_vectorstore(self) -> VectorStore:
        return self.original_input
    
