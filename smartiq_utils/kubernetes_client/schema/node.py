from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import computed_field
from pydantic import Field
from pydantic import IPvAnyNetwork
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta
from smartiq_utils.utils import camel_to_snake


class V1NodeSpec(BaseModel):
    pod_cidr: Optional[IPvAnyNetwork] = Field(
        None, description="PodCIDR represents the pod IP range assigned to the node"
    )


class V1NodeAddress(BaseModel):
    address: str = Field(description="The node address")
    type: Optional[str] = Field(None, description="Node address type, e.g., 'Hostname', 'InternalIP'")


class V1NodeCondition(BaseModel):
    type: str = Field(description="Type of node condition")
    status: str = Field(description="Status of the condition, one of True, False, Unknown")
    last_heartbeat_time: Optional[datetime] = Field(
        None, alias="lastHeartbeatTime", description="Last time we got an update on a given condition"
    )
    last_transition_time: Optional[datetime] = Field(
        None, alias="lastTransitionTime", description="Last time the condition transit from one status to another"
    )
    reason: Optional[str] = Field(None, description="(brief) reason for the condition's last transition")
    message: Optional[str] = Field(None, description="Human readable message indicating details about last transition")


class V1ContainerImage(BaseModel):
    names: List[str] = Field(description="Names by which this image is known")
    size_bytes: Optional[int] = Field(None, description="The size of the image in bytes")


class V1NodeSystemInfo(BaseModel):
    machine_id: str = Field(description="MachineID reported by the node")
    system_uuid: str = Field(description="SystemUUID reported by the node")
    boot_id: str = Field(description="Boot ID reported by the node")
    kernel_version: str = Field(description="Kernel Version reported by the node from 'uname -r'")
    os_image: str = Field(description="OS Image reported by the node from /etc/os-release")
    container_runtime_version: str = Field(
        description="ContainerRuntime Version reported by the node through runtime remote API"
    )
    kubelet_version: str = Field(description="Kubelet Version reported by the node")
    kube_proxy_version: str = Field(description="KubeProxy Version reported by the node")
    operating_system: str = Field(description="The Operating System reported by the node")
    architecture: str = Field(description="The Architecture reported by the node")


class V1NodeStatus(BaseModel):
    addresses: List[V1NodeAddress] = Field(description="List of addresses reachable to the node")
    allocatable: Dict[str, str] = Field(
        description="Allocatable represents the resources of a node that are available for scheduling",
    )
    capacity: Dict[str, str] = Field(description="Capacity represents the total resources of a node")
    conditions: List[V1NodeCondition] = Field(description="Conditions is an array of current observed node conditions")
    images: List[V1ContainerImage] = Field(description="List of container images on this node")
    node_info: V1NodeSystemInfo = Field(description="Set of ids/uuids to uniquely identify the node")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def host_name(self) -> Optional[str]:
        return next((addr.address for addr in self.addresses if addr.type == "Hostname"), None)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def node_ip(self) -> Optional[str]:
        return next((addr.address for addr in self.addresses if addr.type == "InternalIP"), None)


class V1Node(BaseModel):
    api_version: str = Field(default="v1", description="API version of the Node object")
    kind: str = Field(default="Node", description="Kind is always 'Node' for node objects")
    metadata: V1ObjectMeta = Field(description="Standard object's metadata")
    spec: V1NodeSpec = Field(description="Specification of the desired behavior of the node")
    status: V1NodeStatus = Field(description="Most recently observed status of the node")

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        result = {
            "name": self.metadata.name,  # pylint: disable=no-member
            "labels": self.metadata.labels,  # pylint: disable=no-member
            "annotations": self.metadata.annotations,  # pylint: disable=no-member
            "uuid": self.metadata.uid,  # pylint: disable=no-member
            "images": self.status.images if self.status else None,  # pylint: disable=no-member
            "host_name": self.status.host_name if self.status else None,  # pylint: disable=no-member
            "host_ip": self.status.node_ip if self.status else None,  # pylint: disable=no-member
            "system_info": self.status.node_info if self.status else None,  # pylint: disable=no-member
            "pod_cidr": str(self.spec.pod_cidr) if self.spec.pod_cidr else None,  # pylint: disable=no-member
            "allocatable": self.status.allocatable if self.status else None,  # pylint: disable=no-member
            "creation_time": self.metadata.creation_timestamp,  # pylint: disable=no-member
        }
        result.update(
            {
                camel_to_snake(condition.type): condition.status == "True"  # type: ignore[misc]
                for condition in self.status.conditions  # pylint: disable=no-member
            }
        )
        return result


class V1NodeList(BaseModel):
    api_version: str = Field(default="v1", description="API version of the NodeList object")
    kind: str = Field(default="NodeList", description="Kind is always 'NodeList' for node lists")
    items: List[V1Node] = Field(description="List of nodes")
