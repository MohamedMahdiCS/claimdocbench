"""ClaimDocBench: a multilingual, adversarial claim-document benchmark."""

from claimdocbench.adjudication import Adjudication, Decision, Reason, adjudicate
from claimdocbench.policy import Policy, load_policy

__all__ = ["Adjudication", "Decision", "Policy", "Reason", "adjudicate", "load_policy"]
__version__ = "0.1.0.dev0"
