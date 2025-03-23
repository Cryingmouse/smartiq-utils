from datetime import datetime
from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class AppV1StatefulSetSpec(BaseModel):
    replicas: int
    selector: Dict  # label_selector
    service_name: str
    template: Dict  # pod_template_spec
    volume_claim_templates: List[Dict]  # persistent_volume_claim list
    pod_management_policy: str
    update_strategy: Dict  # stateful_set_update_strategy
    revision_history_limit: int
    min_ready_seconds: int
    persistent_volume_claim_retention_policy: Dict


class AppV1StatefulSetCondition(BaseModel):
    type: str
    status: str
    last_transition_time: datetime
    reason: str
    message: str


class AppV1StatefulSetStatus(BaseModel):
    observed_generation: int
    replicas: int
    ready_replicas: int
    current_replicas: int
    updated_replicas: int
    current_revision: str
    update_revision: str
    collision_count: int
    available_replicas: int
    conditions: List[AppV1StatefulSetCondition]

    @field_validator("replicas", "ready_replicas", mode="before")  # noqa
    @classmethod
    def transform_replicas_num(cls, replicas_num):
        return 0 if not replicas_num else replicas_num


class AppV1StatefulSet(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="AppV1StatefulSet")
    metadata: V1ObjectMeta
    status: AppV1StatefulSetStatus

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "namespace": self.metadata.namespace,
            "name": self.metadata.name,
            "replicas": self.status.replicas,
            "ready_replicas": self.status.ready_replicas,
        }


class AppV1StatefulSetList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="StatefulSetList")
    items: List[AppV1StatefulSet]
