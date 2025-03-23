from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class V1ConfigMap(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="V1ConfigMap")
    metadata: V1ObjectMeta
    binary_data: Dict
    data: Dict
    immutable: bool

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "namespace": self.metadata.namespace,
            "name": self.metadata.name,
            "data": self.data,
        }


class V1ConfigMapList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="ConfigMapList")
    items: List[V1ConfigMap]
