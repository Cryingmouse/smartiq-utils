from datetime import datetime
from typing import List
from typing import Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import IPvAnyAddress
from pydantic import model_serializer

from smartiq_utils.kubernetes_client.schema.meta import V1ObjectMeta


class V1PodSpec(BaseModel):
    containers: List["V1Container"] = Field(description="List of containers belonging to the pod")
    volumes: Optional[list] = Field(default=None, description="List of volumes belonging to the pod")
    node_name: Optional[str] = Field(default=None, description="Name of the node where the Pod is running")
    restart_policy: Optional[str] = Field(default=None, description="Restart policy for all containers within the pod")
    service_account_name: Optional[str] = Field(
        default=None, description="Name of the ServiceAccount to use to run this pod"
    )


class V1Container(BaseModel):
    name: str = Field(..., description="Name of the container")
    image: str = Field(..., description="Docker image name")
    ports: Optional[List["V1ContainerPort"]] = Field(
        default=None, description="List of ports to expose from the container"
    )
    env: Optional[List["V1EnvVar"]] = Field(
        default=None, description="List of environment variables to set in the container"
    )


class V1ContainerPort(BaseModel):
    name: Optional[str] = Field(default=None)
    container_port: int = Field(..., description="Number of port to expose on the pod's IP address")
    protocol: Optional[str] = Field(default="UDP", description="Protocol for port. Must be UDP, TCP, or SCTP")
    host_ip: Optional[IPvAnyAddress] = Field(default=None, description="Protocol for port. Must be UDP, TCP, or SCTP")
    host_port: Optional[int] = Field(..., description="Protocol for port. Must be UDP, TCP, or SCTP")


class V1EnvVar(BaseModel):
    name: str = Field(..., description="Name of the environment variable")
    value: Optional[str] = Field(default=None, description="Value of the environment variable")


class V1PodStatus(BaseModel):
    phase: Optional[str] = Field(default=None, description="Current condition of the pod")
    pod_ip: Optional[IPvAnyAddress] = Field(default=None, description="IP address allocated to the pod")
    host_ip: Optional[IPvAnyAddress] = Field(default=None, description="IP address allocated to the pod")
    start_time: Optional[datetime] = Field(default=None, description="Time when the pod was started")
    container_statuses: Optional[List["V1ContainerStatus"]] = Field(
        default=None, description="The list has one entry per container in the manifest"
    )


class V1ContainerStatus(BaseModel):
    name: str = Field(..., description="Name of the container")
    ready: bool = Field(..., description="Specifies whether the container has passed its readiness probe")
    restart_count: int = Field(..., description="The number of times the container has been restarted")
    image: str = Field(..., description="The image the container is running")
    container_id: Optional[str] = Field(
        default=None, description="Container's ID in the format 'docker://<container_id>'"
    )


class V1Pod(BaseModel):
    api_version: Optional[str] = Field(default=None)
    kind: Optional[str] = Field(default=None)
    metadata: V1ObjectMeta = Field(description="Standard object's metadata")
    spec: V1PodSpec = Field(description="Specification of the desired behavior of the pod")
    status: Optional[V1PodStatus] = Field(default=None, description="Most recently observed status of the pod")

    @model_serializer()
    def serialize_model(self):
        containers = [
            {
                "name": container_spec.name,
                "image": container_spec.image,
                "ports": container_spec.ports,
                "env": container_spec.env,
                "restart_count": container_status.restart_count,
            }
            for container_spec, container_status in zip(
                self.spec.containers, self.status.container_statuses  # pylint: disable=no-member
            )
        ]

        is_mirror = False
        if (
            self.metadata.annotations  # pylint: disable=no-member
            and "kubernetes.io/config.mirror" in self.metadata.annotations  # pylint: disable=no-member
        ):
            is_mirror = True

        include_empty_dir = False
        if self.spec.volumes:  # pylint: disable=no-member
            for volume in self.spec.volumes:  # pylint: disable=no-member
                if volume.get("empty_dir", None):
                    include_empty_dir = True

        return {
            "namespace": self.metadata.namespace,  # pylint: disable=no-member
            "owner_references": self.metadata.owner_references,  # pylint: disable=no-member
            "is_mirror": is_mirror,
            "name": self.metadata.name,  # pylint: disable=no-member
            "ip": str(self.status.pod_ip),  # pylint: disable=no-member
            "labels": self.metadata.labels,  # pylint: disable=no-member
            "ready": all(status.ready for status in self.status.container_statuses),  # pylint: disable=no-member
            "containers": containers,
            "node_name": self.spec.node_name,  # pylint: disable=no-member
            "include_empty_dir": include_empty_dir,
            "node_ip": str(self.status.host_ip),  # pylint: disable=no-member
            "creation_timestamp": self.metadata.creation_timestamp,  # pylint: disable=no-member
            "start_time": self.status.start_time,  # pylint: disable=no-member
        }


class V1PodList(BaseModel):
    api_version: str = Field(
        default="v1", description="APIVersion defines the versioned schema of this representation of an object"
    )
    kind: str = Field(
        default="PodList", description="Kind is a string value representing the REST resource this object represents"
    )
    items: List[V1Pod] = Field(..., description="List of pods")
