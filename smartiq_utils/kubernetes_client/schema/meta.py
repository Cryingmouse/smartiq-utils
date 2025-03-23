from datetime import datetime
from typing import Dict
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import UUID4


class V1ObjectMeta(BaseModel):
    name: str
    namespace: Optional[str] = Field(default=None, description="Namespace of the resource")
    resource_version: Optional[str] = Field(default=None, description="Version of the resource")
    labels: Optional[Dict[str, str]] = Field(default=None, description="Map of string keys and values for labels")
    annotations: Optional[Dict[str, str]] = Field(
        default=None, description="Map of string keys and values for annotations"
    )
    uid: Optional[UUID4] = Field(default=None, description="Unique identifier for the object")
    creation_timestamp: Optional[datetime] = Field(default=None, description="Timestamp when the object was created")
    deletion_timestamp: Optional[datetime] = Field(default=None, description="Timestamp when the object was deleted")
    owner_references: Optional[list] = Field(default=None, description="Owner reference")
