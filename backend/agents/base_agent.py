from abc import ABC, abstractmethod


class Agent(ABC):
    """
    Base class for all ProofOfCarbon agents.
    Every agent must implement the `run` method.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, input_data: dict) -> dict:
        """
        Execute the agent's task.

        Args:
            input_data: dict containing the relevant input for the agent.

        Returns:
            dict containing the agent's findings/output.
        """
        pass

    def __repr__(self):
        return f"<Agent: {self.name}>"
