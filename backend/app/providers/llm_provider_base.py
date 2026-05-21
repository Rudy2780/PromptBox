from abc import ABC, abstractmethod

class LLMProvider(ABC):

    @abstractmethod
    async def run_prompt(self, prompt: str):
        pass