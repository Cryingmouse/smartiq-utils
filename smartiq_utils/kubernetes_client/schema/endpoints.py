from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import IPvAnyAddress
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class V1EndpointAddress(BaseModel):
    ip: IPvAnyAddress
    hostname: str
    node_name: str


class V1EndpointPort(BaseModel):
    name: str
    port: int
    protocol: str


class V1EndpointSubset(BaseModel):
    addresses: List[V1EndpointAddress]
    ports: List[V1EndpointPort]


class V1Endpoints(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="V1Endpoints")
    metadata: V1ObjectMeta
    subsets: List[V1EndpointSubset]

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {"namespace": self.metadata.namespace, "name": self.metadata.name, "subsets": self.subsets}


class V1EndpointsList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="EndpointsList")
    items: List[V1Endpoints]
