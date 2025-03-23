import logging
import os
from typing import Any
from typing import Dict
from typing import Union

from kubernetes import client  # type: ignore[import-untyped]
from kubernetes import config
from kubernetes import stream
from kubernetes.client import ApiException  # type: ignore[import-untyped]
from kubernetes.config import ConfigException  # type: ignore[import-untyped]

from smartiq_utils.executor import SystemCallError
from smartiq_utils.kubernetes_client.schema.config_map import V1ConfigMap
from smartiq_utils.kubernetes_client.schema.config_map import V1ConfigMapList
from smartiq_utils.kubernetes_client.schema.deployment import AppV1Deployment
from smartiq_utils.kubernetes_client.schema.deployment import AppV1DeploymentList
from smartiq_utils.kubernetes_client.schema.endpoints import V1Endpoints
from smartiq_utils.kubernetes_client.schema.endpoints import V1EndpointsList
from smartiq_utils.kubernetes_client.schema.ingress import NetworkingV1Ingress
from smartiq_utils.kubernetes_client.schema.ingress import NetworkingV1IngressList
from smartiq_utils.kubernetes_client.schema.node import V1NodeList
from smartiq_utils.kubernetes_client.schema.persistent_volume_claim import V1PersistentVolumeClaim
from smartiq_utils.kubernetes_client.schema.persistent_volume_claim import V1PersistentVolumeClaimList
from smartiq_utils.kubernetes_client.schema.pod import V1Pod
from smartiq_utils.kubernetes_client.schema.pod import V1PodList
from smartiq_utils.kubernetes_client.schema.secret import V1Secret
from smartiq_utils.kubernetes_client.schema.secret import V1SecretList
from smartiq_utils.kubernetes_client.schema.service import V1Service
from smartiq_utils.kubernetes_client.schema.service import V1ServiceList
from smartiq_utils.kubernetes_client.schema.stateful_set import AppV1StatefulSet
from smartiq_utils.kubernetes_client.schema.stateful_set import AppV1StatefulSetList

LOG = logging.getLogger("smartiq_utilsrary")


class KubernetesClient:
    def __init__(self):
        self.core_v1 = None
        self.app_v1 = None
        self.network_v1 = None
        self.load_kubernetes_config()

    def load_kubernetes_config(self):
        try:
            config.load_incluster_config()
            LOG.debug("Loaded in-cluster configuration")
        except ConfigException:
            LOG.debug("Not running inside the cluster, trying running outside the cluster.")
            self._load_external_config()

        self.core_v1 = client.CoreV1Api()
        self.app_v1 = client.AppsV1Api()
        self.network_v1 = client.NetworkingV1Api()

    def _load_external_config(self):
        if "KUBECONFIG" in os.environ:
            self._try_load_config(os.environ["KUBECONFIG"], "KUBECONFIG")
            return

        k3s_config = "/etc/rancher/k3s/k3s.yaml"
        if os.path.exists(k3s_config) and os.access(k3s_config, os.R_OK):
            self._try_load_config(k3s_config, "K3s configuration")
            return

        try:
            config.load_kube_config()
            LOG.debug("Loaded default kubeconfig")
        except ConfigException as e:
            LOG.exception(f"Failed to load default kubeconfig. Reason: {e}")
            raise ConfigException("Could not configure kubernetes python client") from e

    def _try_load_config(self, config_file: str, config_name: str) -> None:
        try:
            config.load_kube_config(config_file=config_file)
            LOG.debug(f"Loaded {config_name} from {config_file}")
        except ConfigException as e:
            LOG.error(f"Failed to load {config_name} from {config_file}")
            raise ConfigException("Could not configure kubernetes python client") from e

    def patch_node(self, name, body, **kwargs) -> None:
        self.core_v1.patch_node(self, name, body, **kwargs)  # pylint: disable=too-many-function-args

    def list_node(self) -> dict:
        node_list = self.core_v1.list_node(watch=False)
        return V1NodeList.model_validate(node_list.to_dict()).model_dump(mode="json")

    def delete_node(self, name: str, **kwargs) -> None:
        try:
            self.core_v1.delete_node(name, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_pod(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.core_v1.create_namespaced_pod(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_pod(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.patch_namespaced_pod(name, namespace, body, **kwargs)

    def evict_pod(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.create_namespaced_pod_eviction(name, namespace, body, **kwargs)

    def get_namespaced_pod(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            pod = self.core_v1.read_namespaced_pod(name, namespace, **kwargs)
            return V1Pod.model_validate(pod.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_pod(self, namespace: str, **kwargs) -> dict:
        pod_list = self.core_v1.list_namespaced_pod(namespace, **kwargs)
        return V1PodList.model_validate(pod_list.to_dict()).model_dump(mode="json")

    def list_pod(self, **kwargs) -> dict:
        pod_list = self.core_v1.list_pod_for_all_namespaces(watch=False, **kwargs)
        return V1PodList.model_validate(pod_list.to_dict()).model_dump(mode="json")

    def delete_pod(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.core_v1.delete_namespaced_pod(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_secret(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.core_v1.create_namespaced_secret(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_secret(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.patch_namespaced_secret(name, namespace, body, **kwargs)

    def get_namespaced_secret(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            secret = self.core_v1.read_namespaced_secret(name, namespace, **kwargs)
            return V1Secret.model_validate(secret.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_secret(self, namespace: str, **kwargs) -> dict:
        secret_list = self.core_v1.list_namespaced_secret(namespace, **kwargs)
        return V1SecretList.model_validate(secret_list.to_dict()).model_dump(mode="json")

    def list_secret(self) -> dict:
        secret_list = self.core_v1.list_secret_for_all_namespaces(watch=False)
        return V1SecretList.model_validate(secret_list.to_dict()).model_dump(mode="json")

    def delete_secret(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.core_v1.delete_namespaced_secret(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_stateful_set(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.app_v1.create_namespaced_stateful_set(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_stateful_set(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.app_v1.patch_namespaced_stateful_set(name, namespace, body, **kwargs)

    def patch_stateful_set_scale(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.app_v1.patch_namespaced_stateful_set_scale(name, namespace, body, **kwargs)

    def get_namespaced_stateful_set(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            stateful_set = self.app_v1.read_namespaced_stateful_set(name, namespace, **kwargs)
            return AppV1StatefulSet.model_validate(stateful_set.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_stateful_set(self, namespace: str, **kwargs) -> dict:
        stateful_set_list = self.app_v1.list_namespaced_stateful_set(namespace, **kwargs)
        return AppV1StatefulSetList.model_validate(stateful_set_list.to_dict()).model_dump(mode="json")

    def list_stateful_set(self) -> dict:
        stateful_set_list = self.app_v1.list_stateful_set_for_all_namespaces(watch=False)
        return AppV1StatefulSetList.model_validate(stateful_set_list.to_dict()).model_dump(mode="json")

    def delete_stateful_set(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.app_v1.delete_namespaced_stateful_set(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_deployment(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.app_v1.create_namespaced_deployment(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_deployment(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.app_v1.patch_namespaced_deployment(name, namespace, body, **kwargs)

    def patch_deployment_scale(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.app_v1.patch_namespaced_deployment_scale(name, namespace, body, **kwargs)

    def get_namespaced_deployment_scale(self, name: str, namespace: str, **kwargs) -> Any:
        return self.app_v1.read_namespaced_deployment_scale(name, namespace, **kwargs)

    def get_namespaced_deployment(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            deployment = self.app_v1.read_namespaced_deployment(name, namespace, **kwargs)
            return AppV1Deployment.model_validate(deployment.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_deployment(self, namespace: str, **kwargs) -> dict:
        deployment_list = self.app_v1.list_namespaced_deployment(namespace, **kwargs)
        return AppV1DeploymentList.model_validate(deployment_list.to_dict()).model_dump(mode="json")

    def list_deployment(self) -> dict:
        deployment_list = self.app_v1.list_deployment_for_all_namespaces(watch=False)
        return AppV1DeploymentList.model_validate(deployment_list.to_dict()).model_dump(mode="json")

    def delete_deployment(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.app_v1.delete_namespaced_deployment(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_persistent_volume_claim(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.core_v1.create_namespaced_persistent_volume_claim(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_persistent_volume_claim(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.patch_namespaced_persistent_volume_claim(name, namespace, body, **kwargs)

    def get_namespaced_persistent_volume_claim(
        self, name: str, namespace: str, **kwargs
    ) -> Union[Dict[str, Any], None]:
        try:
            persistent_volume_claim = self.core_v1.read_namespaced_persistent_volume_claim(name, namespace, **kwargs)
            return V1PersistentVolumeClaim.model_validate(persistent_volume_claim.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_persistent_volume_claim(self, namespace: str, **kwargs) -> dict:
        pvc_list = self.core_v1.list_namespaced_persistent_volume_claim(namespace, **kwargs)
        return V1PersistentVolumeClaimList.model_validate(pvc_list.to_dict()).model_dump(mode="json")

    def list_persistent_volume_claim(self) -> dict:
        pvc_list = self.core_v1.list_persistent_volume_claim_for_all_namespaces(watch=False)
        return V1PersistentVolumeClaimList.model_validate(pvc_list.to_dict()).model_dump(mode="json")

    def delete_persistent_volume_claim(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.core_v1.delete_namespaced_persistent_volume_claim(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_service(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.core_v1.create_namespaced_service(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_service(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.patch_namespaced_service(name, namespace, body, **kwargs)

    def get_namespaced_service(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            service = self.core_v1.read_namespaced_service(name, namespace, **kwargs)
            return V1Service.model_validate(service.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_service(self, namespace: str, **kwargs) -> dict:
        service_list = self.core_v1.list_namespaced_service(namespace, **kwargs)
        return V1ServiceList.model_validate(service_list.to_dict()).model_dump(mode="json")

    def list_service(self) -> dict:
        service_list = self.core_v1.list_service_for_all_namespaces(watch=False)
        return V1ServiceList.model_validate(service_list.to_dict()).model_dump(mode="json")

    def delete_service(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.core_v1.delete_namespaced_service(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_endpoints(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.core_v1.create_namespaced_endpoints(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_endpoints(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.patch_namespaced_endpoints(name, namespace, body, **kwargs)

    def get_namespaced_endpoints(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            endpoints = self.core_v1.read_namespaced_endpoints(name, namespace, **kwargs)
            return V1Endpoints.model_validate(endpoints.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_endpoints(self, namespace: str, **kwargs) -> dict:
        endpoints_list = self.core_v1.list_namespaced_endpoints(namespace, **kwargs)
        return V1EndpointsList.model_validate(endpoints_list.to_dict()).model_dump(mode="json")

    def list_endpoints(self) -> dict:
        endpoints_list = self.core_v1.list_endpoints_for_all_namespaces(watch=False)
        return V1EndpointsList.model_validate(endpoints_list.to_dict()).model_dump(mode="json")

    def delete_endpoints(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.core_v1.delete_namespaced_endpoints(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_ingress(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.network_v1.create_namespaced_ingress(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_ingress(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.network_v1.patch_namespaced_ingress(name, namespace, body, **kwargs)

    def get_namespaced_ingress(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            endpoints = self.network_v1.read_namespaced_ingress(name, namespace, **kwargs)
            return NetworkingV1Ingress.model_validate(endpoints.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_ingress(self, namespace: str, **kwargs) -> dict:
        ingress_list = self.network_v1.list_namespaced_ingress(namespace, **kwargs)
        return NetworkingV1IngressList.model_validate(ingress_list.to_dict()).model_dump(mode="json")

    def list_ingress(self) -> dict:
        ingress_list = self.network_v1.list_ingress_for_all_namespaces(watch=False)
        return NetworkingV1IngressList.model_validate(ingress_list.to_dict()).model_dump(mode="json")

    def delete_ingress(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.network_v1.delete_namespaced_ingress(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def create_config_map(self, namespace: str, body: dict, **kwargs) -> None:
        try:
            self.core_v1.create_namespaced_config_map(namespace, body, **kwargs)
        except ApiException as e:
            if e.status != 409:
                raise e

    def patch_config_map(self, name: str, namespace: str, body: dict, **kwargs) -> None:
        self.core_v1.patch_namespaced_config_map(name, namespace, body, **kwargs)

    def get_namespaced_config_map(self, name: str, namespace: str, **kwargs) -> Union[Dict[str, Any], None]:
        try:
            endpoints = self.core_v1.read_namespaced_config_map(name, namespace, **kwargs)
            return V1ConfigMap.model_validate(endpoints.to_dict()).model_dump(mode="json")
        except ApiException as e:
            if e.status != 404:
                raise e

            return None

    def list_namespaced_config_map(self, namespace: str, **kwargs) -> dict:
        config_map_list = self.core_v1.list_namespaced_config_map(namespace, **kwargs)
        return V1ConfigMapList.model_validate(config_map_list.to_dict()).model_dump(mode="json")

    def list_config_map(self) -> dict:
        config_map_list = self.core_v1.list_config_map_for_all_namespaces(watch=False)
        return V1ConfigMapList.model_validate(config_map_list.to_dict()).model_dump(mode="json")

    def delete_config_map(self, name: str, namespace: str, **kwargs) -> None:
        try:
            self.core_v1.delete_namespaced_config_map(name, namespace, **kwargs)
        except ApiException as e:
            if e.status != 404:
                raise e

    def exec_command_in_pod(self, name: str, namespace: str, command: list) -> tuple:
        stream_client = None
        try:
            stream_client = stream.stream(
                self.core_v1.connect_get_namespaced_pod_exec,
                name,
                namespace,
                command=command,
                stderr=True,
                stdin=True,
                stdout=True,
                tty=True,
                _preload_content=False,
            )
            stream_client.run_forever(timeout=10)
            data = stream_client.read_stdout().replace("\r\n", "\n")
            if stream_client.returncode == 0:
                return stream_client.returncode, data

            raise SystemCallError(
                stream_client.returncode,
                data,
                stream_client.read_stderr().replace("\r\n", "\n") or data,
            )
        finally:
            if stream_client:
                stream_client.close()
