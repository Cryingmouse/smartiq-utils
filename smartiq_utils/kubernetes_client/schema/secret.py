from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class V1Secret(BaseModel):
    api_version: Optional[str] = Field(default=None)
    kind: Optional[str] = Field(default=None)
    type: Optional[str] = Field(default=None)
    metadata: V1ObjectMeta = Field(description="Standard object's metadata")
    data: Optional[dict] = Field(default=None, description="Data of secret object")

    @model_serializer()
    def serialize_model(self):
        return {
            "namespace": self.metadata.namespace,  # pylint: disable=no-member
            "name": self.metadata.name,  # pylint: disable=no-member
            "creation_timestamp": self.metadata.creation_timestamp,  # pylint: disable=no-member
            "data": self.data,
        }


class V1SecretList(BaseModel):
    api_version: str = Field(
        default="v1", description="APIVersion defines the versioned schema of this representation of an object"
    )
    kind: str = Field(
        default="SecretList", description="Kind is a string value representing the REST resource this object represents"
    )
    items: List[V1Secret] = Field(description="List of secrets")
