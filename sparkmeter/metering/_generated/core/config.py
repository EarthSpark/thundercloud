
from dataclasses import dataclass
@dataclass
class ClientConfig:
    base_url: str
    timeout: float | None = 30.0
