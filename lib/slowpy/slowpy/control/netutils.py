#!/usr/bin/env python3

import os, re, shutil, subprocess, ipaddress, logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from slowpy.control import ControlException

MAC_RE = re.compile(r"^[0-9a-fA-F]{2}(:[0-9a-fA-F]{2}){5}$")


def find_ip(mac:str, **kwargs):
    return IPFinder().find(mac, **kwargs)


class IPFinder:
    def __init__(self):
        pass

    
    def find(self, mac:str, *, use_arp_cache=True, interface:str|None=None, cidr:str|None=None):
        max_hosts = 256
        workers = 8
        timeout = 1

        mac = mac.lower().replace('-', ':')
        if not MAC_RE.match(mac):
            raise ControlException("IPFinder: Invalid MAC format")
        logging.debug(f'IPFinder: Searching IP for {mac}')
    
        # look at the cache first
        if use_arp_cache:
            found = self._ip_from_mac_in_neigh(mac)
            if found:
                logging.info(f'IP Found in ARP cache: {found}')
                return found

        if shutil.which("ip") is None or shutil.which("ping") is None:
            raise ControlException("IPFinder: Required commands not found: ip, ping")

        if cidr is None:
            iface = interface or self._get_default_iface()
            if not iface:
                raise ControlException("IPFinder: Could not determine default interface")
            logging.debug(f'IPFinder: Interface: {iface}')

        iface_cidr = cidr or self._get_iface_cidr(iface)
        if not iface_cidr:
            raise ControlException(f"Could not get IPv4 address/prefix for interface {iface}")
        # 192.168.1.10/24 -> 192.168.1.0/24
        net = ipaddress.ip_network(iface_cidr, strict=False)
        cidr = str(net)
        logging.debug(f'IPFinder: IPv4 address/prefix: {cidr}')

        net = ipaddress.ip_network(cidr, strict=False)
        host_count = net.num_addresses - 2 if net.num_addresses >= 2 else 0
        if host_count > max_hosts:
            raise SystemExit(f"Refusing to scan {host_count} hosts (> {max_hosts})")

        # ping scans to pupulate the ARP table
        def generate_hosts(cidr: str):
            net = ipaddress.ip_network(cidr, strict=False)
            for ip in net.hosts():
                yield str(ip)
        ips = list(generate_hosts(cidr))

        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = [ex.submit(self._ping_once, ip, timeout) for ip in ips]
            for _ in as_completed(futures):
                found = self._ip_from_mac_in_neigh(mac)
                if found:
                    logging.info(f'IP Found: {found}')
                    return found
            
        return None


    def _get_default_iface(self) -> str | None:
        # ip route show default -> "default via ... dev eth0 ..."
        out = self._run_command(["ip", "route", "show", "default"])
        m = re.search(r"\bdev\s+(\S+)", out)
        return m.group(1) if m else None


    def _get_iface_cidr(self, iface: str) -> str | None:
        # ip -4 addr show dev eth0 -> "inet 192.168.1.10/24 ..."
        out = self._run_command(["ip", "-4", "addr", "show", "dev", iface])
        m = re.search(r"\binet\s+(\d+\.\d+\.\d+\.\d+/\d+)\b", out)
        return m.group(1) if m else None


    def _ping_once(self, ip: str, timeout_s: float = 0.8) -> None:
        # -n: no DNS lookup, -c 1: only one try, -W: timeout
        logging.debug(f"IPFinder: pinging to {ip}")
        subprocess.run(
            ["ping", "-n", "-c", "1", "-W", str(int(max(1, round(timeout_s)))) , ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


    def _ip_from_mac_in_neigh(self, target_mac: str) -> str | None:
        target_mac = target_mac.lower()
        out = self._run_command(["ip", "neigh"])
        for line in out.splitlines():
            # example: 192.168.1.42 dev eth0 lladdr aa:bb:cc:dd:ee:ff REACHABLE
            m = re.search(r"^(\S+).*\blladdr\s+([0-9a-f:]{17})\b", line.lower())
            if m:
                ip, mac = m.group(1), m.group(2)
                if mac == target_mac:
                    if "incomplete" not in line.lower():
                        return ip
        return None


    def _run_command(self, cmd: list[str]) -> str:
        p = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, check=False
        )
        return p.stdout



if __name__ == "__main__":
    print(find_ip('d8:3a:dd:e4:b9:9f', use_arp_cache=False))
