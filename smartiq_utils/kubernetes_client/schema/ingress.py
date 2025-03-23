from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class NetworkingV1Ingress(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="NetworkingV1Ingresss")
    metadata: V1ObjectMeta
    spec: Dict
    status: Dict

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "namespace": self.metadata.namespace,
            "name": self.metadata.name,
        }


class NetworkingV1IngressList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="IngressList")
    items: List[NetworkingV1Ingress]
