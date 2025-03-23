from datetime import datetime
from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class V1PersistentVolumeClaimSpec(BaseModel):
    access_modes: List[str]
    resources: Dict
    volume_name: str
    storage_class_name: str
    volume_mode: str
    data_source: Dict


class V1PersistentVolumeClaimCondition(BaseModel):
    type: str
    status: str
    last_probe_time: datetime
    last_transition_time: datetime


class V1PersistentVolumeClaimStatusCapacity(BaseModel):
    storage: str


class V1PersistentVolumeClaimStatus(BaseModel):
    phase: str
    access_modes: List[str]
    capacity: V1PersistentVolumeClaimStatusCapacity
    conditions: List[V1PersistentVolumeClaimCondition]


class V1PersistentVolumeClaim(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="V1PersistentVolumeClaim")
    metadata: V1ObjectMeta
    spec: V1PersistentVolumeClaimSpec
    status: V1PersistentVolumeClaimStatus

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "namespace": self.metadata.namespace,
            "name": self.metadata.name,
            "annotations": self.metadata.annotations,
            "capacity": self.status.capacity.storage if self.status.capacity else None,
            "volume_name": self.spec.volume_name,
        }


class V1PersistentVolumeClaimList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="PersistentVolumeClaimList")
    items: List[V1PersistentVolumeClaim]
