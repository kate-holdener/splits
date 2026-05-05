from discovery.network_discovery import NetworkScanner
from discovery.rfid_discovery import RFIDDiscovery


class TestRFIDDiscovery:
    def test_get_local_subnets_uses_local_addresses_and_arp_cache(self, monkeypatch):
        monkeypatch.setattr(
            RFIDDiscovery,
            "_get_local_ipv4_addresses",
            classmethod(lambda cls: ["192.168.50.23", "169.254.45.10", "127.0.0.1"]),
        )
        monkeypatch.setattr(
            RFIDDiscovery,
            "_get_subnets_from_arp_cache",
            classmethod(lambda cls: ["10.0.0", "192.168.50"]),
        )

        assert RFIDDiscovery.get_local_subnets() == [
            "192.168.50",
            "169.254.45",
            "127.0.0",
            "10.0.0",
        ]

    def test_get_arp_hosts_filters_to_local_subnets(self, monkeypatch):
        arp_output = """
? (192.168.50.10) at aa:bb:cc:dd:ee:ff on en0 ifscope [ethernet]
? (192.168.50.0) at aa:bb:cc:dd:ee:01 on en0 ifscope [ethernet]
? (10.0.0.20) at aa:bb:cc:dd:ee:11 on en0 ifscope [ethernet]
? (172.20.1.30) at aa:bb:cc:dd:ee:22 on en0 ifscope [ethernet]
? (192.168.50.77) at (incomplete) on en0 ifscope [ethernet]
""".strip()

        monkeypatch.setattr(RFIDDiscovery, "get_local_subnets", classmethod(lambda cls: ["192.168.50", "10.0.0"]))
        monkeypatch.setattr(
            "discovery.rfid_discovery.subprocess.check_output",
            lambda *args, **kwargs: arp_output,
        )

        assert RFIDDiscovery.get_arp_hosts() == ["192.168.50.10", "10.0.0.20"]


class TestNetworkScanner:
    def test_ip_to_subnet_keeps_loopback_for_simulator(self):
        assert RFIDDiscovery._ip_to_subnet("127.0.0.1") == "127.0.0"

    def test_scan_subnet_checks_priority_addresses_before_full_sweep(self, monkeypatch):
        scanner = NetworkScanner()
        calls = []

        def fake_scan_hosts(addresses):
            calls.append(addresses)
            return []

        monkeypatch.setattr(scanner, "scan_hosts", fake_scan_hosts)

        scanner.scan_subnet("192.168.1", max_hosts=12)

        assert calls[0] == [
            "192.168.1.1",
            "192.168.1.2",
            "192.168.1.3",
            "192.168.1.4",
            "192.168.1.5",
            "192.168.1.10",
            "192.168.1.11",
            "192.168.1.12",
        ]
        assert calls[1] == [
            "192.168.1.6",
            "192.168.1.7",
            "192.168.1.8",
            "192.168.1.9",
        ]

    def test_scan_subnet_stops_after_priority_match(self, monkeypatch):
        scanner = NetworkScanner()
        calls = []

        def fake_scan_hosts(addresses):
            calls.append(addresses)
            return [{"address": "192.168.1.10", "protocol": "llrp", "port": 5084}]

        monkeypatch.setattr(scanner, "scan_hosts", fake_scan_hosts)

        results = scanner.scan_subnet("192.168.1", max_hosts=20)

        assert len(calls) == 1
        assert results == [{"address": "192.168.1.10", "protocol": "llrp", "port": 5084}]
