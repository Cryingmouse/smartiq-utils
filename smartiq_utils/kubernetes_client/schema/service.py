from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator
from pydantic import IPvAnyAddress
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class V1ServiceSpecServicePort(BaseModel):
    name: str
    protocol: str
    port: int
    target_port: Optional[Union[str, int]] = Field(None)
    node_port: int


class V1ServiceSpec(BaseModel):
    ports: Optional[List[V1ServiceSpecServicePort]] = Field(None)
    selector: Dict
    cluster_ip: IPvAnyAddress
    cluster_i_ps: List[str]
    type: str
    external_i_ps: List[str]
    session_affinity: str
    load_balancer_ip: str
    load_balancer_source_ranges: List[str]
    external_name: str
    external_traffic_policy: str
    health_check_node_port: int
    publish_not_ready_addresses: bool
    session_affinity_config: Dict
    ip_families: List[str]
    ip_family_policy: str

    @field_validator("cluster_ip", mode="before")  # noqa
    @classmethod
    def transform_cluster_ip(cls, cluster_ip):
        return None if cluster_ip == "None" else cluster_ip


class V1ServiceLoadBalancerIngress(BaseModel):
    ip: Optional[str] = Field(None)
    hostname: str


class V1ServiceLoadBalancerStatus(BaseModel):
    ingress: List[V1ServiceLoadBalancerIngress]


class V1ServiceStatus(BaseModel):
    load_balancer: V1ServiceLoadBalancerStatus
    condition: list


class V1Service(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="V1Service")
    metadata: V1ObjectMeta
    spec: V1ServiceSpec

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "namespace": self.metadata.namespace,
            "name": self.metadata.name,
            "cluster_ip": str(self.spec.cluster_ip),
        }


class V1ServiceList(BaseModel):
    api_version: str = Field(default="v1")
    kind: str = Field(default="ServiceList")
    items: List[V1Service]
