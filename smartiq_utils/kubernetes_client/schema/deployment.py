from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class AppV1TemplateSpecContainer(BaseModel):
    name: str
    image: str
    ports: Optional[list] = Field(default=None)
    env: Optional[list] = Field(default=None)


class AppV1TemplateSpec(BaseModel):
    containers: List[AppV1TemplateSpecContainer]
    init_containers: List[AppV1TemplateSpecContainer]
    affinity: Dict


class AppV1DeploymentSpecTemplate(BaseModel):
    metadata: Dict
    spec: AppV1TemplateSpec


class AppV1DeploymentSpec(BaseModel):
    replicas: int
    selector: Dict
    template: AppV1DeploymentSpecTemplate
    strategy: Dict
    min_ready_seconds: int
    revision_history_limit: int
    paused: bool
    progress_deadline_seconds: int


class AppV1DeploymentCondition(BaseModel):
    type: str
    status: str
    last_update_time: datetime
    last_transition_time: datetime
    reason: str
    message: str


class AppV1DeploymentStatus(BaseModel):
    observed_generation: int
    replicas: int
    updated_replicas: int
    ready_replicas: int
    available_replicas: int
    unavailable_replicas: int
    conditions: List[AppV1DeploymentCondition]

    @field_validator("replicas", "ready_replicas", mode="before")  # noqa
    @classmethod
    def transform_replicas_num(cls, replicas_num):
        return 0 if not replicas_num else replicas_num


class AppV1Deployment(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="AppV1Deployment")
    metadata: V1ObjectMeta
    spec: AppV1DeploymentSpec
    status: AppV1DeploymentStatus

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "namespace": self.metadata.namespace,
            "name": self.metadata.name,
            "creation_timestamp": self.metadata.creation_timestamp,
            "deletion_timestamp": self.metadata.deletion_timestamp,
            "resource_version": self.metadata.resource_version,
            "labels": self.metadata.labels,
            "replicas": self.status.replicas,
            "ready_replicas": self.status.ready_replicas,
            "revision_history_limit": self.spec.revision_history_limit,
            "selector": self.spec.selector,
            "strategy": self.spec.strategy,
            "containers": self.spec.template.spec.containers,
            "affinity": self.spec.template.spec.affinity,
        }


class AppV1DeploymentList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="DeploymentList")
    items: List[AppV1Deployment]
