"""
Zabbix implementation of the Maas class. Retrieves the utilisation and
 saturation values in the zabbix server.
"""
from sdk.mcn import monitoring
import maas


class ZabbixMaas(maas.Maas):
    """
    Maas for Zabbix metric server.
    """
    def __init__(self, zabbix_server_ip):
        # init zabbix server API
        self.zabbix_server = monitoring.ZabbixMonitoring()
        self.zabbix_server.set_address(zabbix_server_ip)

    def _get_metric(self, node, metric):
        """
        Given a node and metric name, this method retrieves the last metric
        value that was updated.
        :param node:  The hostname of the node.
        :param metric: The name of the metric
        :return: The metric value for a given node.
        """
        return self.zabbix_server.get_metric(node, metric)

    def get_compute_saturation(self, node):
        saturation = self._get_metric(node, "compute_saturation")
        return float(saturation)

    def get_compute_utilisation(self, node):
        utilisation = self._get_metric(node, "compute_utilisation")
        return float(utilisation)

    def get_memory_utilisation(self, node):
        return self._get_metric(node, "memory_utilisation")

    def get_memory_saturation(self, node):
        return self._get_metric(node, "memory_saturation")

    def get_storage_utilisation(self, node, mountpoint):
        device_name = mountpoint.split('/')[-1]
        metric = "storage_utilisation_{}".format(device_name)
        metric_val = float(self._get_metric(node, metric))
        return metric_val

    def get_storage_saturation(self, node, mountpoint):
        device_name = mountpoint.split('/')[-1]
        metric = "storage_saturation_{}".format(device_name)
        metric_val = float(self._get_metric(node, metric))
        return metric_val

    def get_network_utilisation(self, node, port, bandwidth=1000000):
        """
        Returns the network utilisation for a network port on the VM.
        :param node: The name of the node connected to the network port.
        :param bandwidth: Bandwidth for the network port.
        :param port: The network interface. E.g "eth0", "eth1"
        :return: The network utilisation for the given node.
        """

        tx_metric = "Outgoing network traffic on ${}".format(port + 1)
        rx_metric = "Incoming network traffic on ${}".format(port + 1)
        tx_bytes = self._get_metric(node, tx_metric)
        rx_bytes = self._get_metric(node, rx_metric)
        total_traffic = float(tx_bytes) + float(rx_bytes)
        utilisation = total_traffic / bandwidth
        # TODO: Remove hack below
        util  = (utilisation / 16) * 100
        return util

    def get_network_saturation(self, node, port):
        """
        Returns the network saturation for a network port on the VM.

        :param node: The name of the node connected to the network port.
        :param port: The network interface. E.g "eth0", "eth1"
        :return: The network saturation for the given node.
        """
        tx_overrun_metric = "tx_overruns_eth{}".format(port)
        rx_overrun_metric = "rx_overruns_eth{}".format(port)
        tx_overrun = self._get_metric(node, tx_overrun_metric)
        rx_overrun = self._get_metric(node, rx_overrun_metric)
        saturation = float(tx_overrun) + float(rx_overrun)
        # TODO: Remove hack below
        sat = (saturation / 16000) * 100
        return saturation
