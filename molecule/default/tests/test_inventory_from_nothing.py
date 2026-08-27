"""
=== STARFALL DEFENCE CORPS ACADEMY ===
ARIA Automated Verification — Mission 1.6: Inventory from Nothing
================================================================

The cadet is given ONLY the subnet 172.30.0.0/24. They must discover the fleet
from the recon node (sdc-ops), fingerprint each node's role from its open port,
build a grouped inventory, produce a facts-backed fleet report, and finally a
DYNAMIC inventory that survives Nyx's live IP rotation.

Everything ARIA needs to know is ground truth in .lab/baseline.json (written by
setup-lab.sh, gitignored): the randomised IPs, each node's role, and a per-host
nonce planted as an Ansible local fact — retrievable ONLY by a live facts sweep.
ARIA runs all discovery/ansible commands inside sdc-ops via `docker exec`, and
re-derives truth itself rather than trusting the cadet's files.
"""
import json
import os
import random
import re
import subprocess
import time

import pytest
import yaml

ROLE_PORT = {"web_servers": 80, "db_servers": 5432, "comms_relays": 6379}
ROLE_GROUPS = list(ROLE_PORT.keys())
OPS = "sdc-ops"


# --------------------------------------------------------------------------- #
# Paths / lab plumbing
# --------------------------------------------------------------------------- #
def _root_dir():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, "..", "..", ".."))


def _ws(rel):
    return os.path.join(_root_dir(), "workspace", rel)


def _baseline_path():
    return os.path.join(_root_dir(), ".lab", "baseline.json")


def _load_baseline():
    with open(_baseline_path()) as f:
        return json.load(f)


def _ops_running():
    r = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", OPS],
        capture_output=True, text=True,
    )
    return r.returncode == 0 and r.stdout.strip() == "true"


def in_ops(cmd, timeout=90):
    """Run a shell command inside sdc-ops as cadet, in the workspace dir."""
    return subprocess.run(
        ["docker", "exec", "-u", "cadet", "-w", "/home/cadet/workspace",
         OPS, "bash", "-lc", cmd],
        capture_output=True, text=True, timeout=timeout,
    )


@pytest.fixture
def baseline():
    """Fresh ground truth each test; skip (not fail) if the lab is down."""
    if not _ops_running():
        pytest.skip("Recon node sdc-ops is not running — run 'make setup'.")
    if not os.path.isfile(_baseline_path()):
        pytest.skip("No range baseline found — run 'make setup'.")
    return _load_baseline()


def _managed(baseline):
    return {m["ip"]: m for m in baseline["managed"]}


# --------------------------------------------------------------------------- #
# Helpers for reading the cadet's artefacts
# --------------------------------------------------------------------------- #
IP_RE = re.compile(r"\b(172\.30\.0\.\d{1,3})\b")


def _read_ws(rel):
    path = _ws(rel)
    if not os.path.isfile(path):
        return None
    with open(path) as f:
        return f.read()


def _load_yaml_ws(rel):
    txt = _read_ws(rel)
    if txt is None:
        return None
    return yaml.safe_load(txt)


# --------------------------------------------------------------------------- #
# Live-inventory + facts helpers (run inside sdc-ops)
# --------------------------------------------------------------------------- #
def _inventory_list(inv_rel):
    """`ansible-inventory -i <inv> --list` parsed to dict, or None on error."""
    r = in_ops(f"ansible-inventory -i {inv_rel} --list 2>/dev/null")
    if r.returncode != 0 or not r.stdout.strip():
        return None
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


def _resolve_group_hosts(data, group):
    """Transitive hosts of an ansible-inventory group (children + hosts)."""
    seen, out = set(), set()

    def rec(g):
        if g in seen:
            return
        seen.add(g)
        node = data.get(g, {})
        if isinstance(node, dict):
            for h in node.get("hosts", []):
                out.add(h)
            for c in node.get("children", []):
                rec(c)

    rec(group)
    return out


def _all_hosts(data):
    meta = data.get("_meta", {}).get("hostvars", {})
    hosts = set(meta.keys())
    return hosts | _resolve_group_hosts(data, "all")


def _gather_live_facts(ips):
    """Authoritative facts for each ip, gathered fresh inside sdc-ops."""
    inv = "\\n".join(["[all]"] + list(ips))
    in_ops(f"printf '{inv}\\n' > /tmp/gr_inv.ini && rm -rf /tmp/gr_facts")
    in_ops("ansible all -i /tmp/gr_inv.ini -m setup --tree /tmp/gr_facts "
           ">/dev/null 2>&1", timeout=120)
    facts = {}
    for ip in ips:
        r = in_ops(f"cat /tmp/gr_facts/{ip} 2>/dev/null")
        if r.returncode == 0 and r.stdout.strip():
            try:
                facts[ip] = json.loads(r.stdout).get("ansible_facts", {})
            except json.JSONDecodeError:
                pass
    return facts


# --------------------------------------------------------------------------- #
# Live IP rotation (Phase 5) — save / rotate / restore so the static-inventory
# phases stay idempotent while the dynamic inventory is proven against new IPs.
# --------------------------------------------------------------------------- #
def _apply_rotation(mapping):
    """mapping: list of (container, new_ip, new_nonce). Live-moves each node."""
    for node, ip, nonce in mapping:
        subprocess.run(["docker", "network", "disconnect", "fleet_net", node],
                       capture_output=True, text=True)
        subprocess.run(["docker", "network", "connect", "--ip", ip,
                        "fleet_net", node], capture_output=True, text=True)
        subprocess.run(
            ["docker", "exec", node, "bash", "-c",
             f"echo '{nonce}' > /etc/sdc/nonce"],
            capture_output=True, text=True,
        )


def _write_baseline_ips(mapping):
    b = _load_baseline()
    by_node = {n: (ip, nonce) for n, ip, nonce in mapping}
    for m in b["managed"]:
        if m["token"] in by_node:
            m["ip"], m["nonce"] = by_node[m["token"]]
    b["rotation_seq"] = b.get("rotation_seq", 0) + 1
    with open(_baseline_path(), "w") as f:
        json.dump(b, f, indent=2)


@pytest.fixture(scope="class")
def rotation():
    """Rotate all managed nodes to fresh IPs, then restore on teardown."""
    if not _ops_running() or not os.path.isfile(_baseline_path()):
        pytest.skip("Lab not live — run 'make setup'.")
    b = _load_baseline()
    old = [(m["token"], m["ip"], m["nonce"]) for m in b["managed"]]
    used = {1, 10, int(b["decoy"]["ip"].split(".")[-1])}
    used |= {int(ip.split(".")[-1]) for _, ip, _ in old}
    pool = [o for o in range(20, 241) if o not in used]
    random.shuffle(pool)
    new = [(tok, f"172.30.0.{pool[i]}",
            "".join(random.choice("0123456789abcdef") for _ in range(16)))
           for i, (tok, _, _) in enumerate(old)]

    _apply_rotation(new)
    _write_baseline_ips(new)
    time.sleep(3)
    try:
        yield
    finally:
        # Restore original addressing + nonces + baseline so re-runs are stable.
        _apply_rotation(old)
        _write_baseline_ips(old)
        time.sleep(2)


# =========================================================================== #
# Phase 1 — Recon Sweep
# =========================================================================== #
class TestReconSweep:
    def test_live_hosts_file_exists(self, baseline):
        assert _read_ws("recon/live-hosts.txt") is not None, (
            "ARIA: No recon sweep found at workspace/recon/live-hosts.txt. "
            "Board the recon node (make shell) and sweep the subnet: "
            "`nmap -sn 172.30.0.0/24`. Record the live hosts you find."
        )

    def test_all_managed_hosts_discovered(self, baseline):
        txt = _read_ws("recon/live-hosts.txt")
        if txt is None:
            pytest.skip("No recon sweep yet")
        found = set(IP_RE.findall(txt))
        missing = [ip for ip in _managed(baseline) if ip not in found]
        assert not missing, (
            f"ARIA: Your sweep missed live fleet nodes: {', '.join(missing)}. "
            "Do not assume the addresses — the fleet is not where you last "
            "left it. Scan the whole subnet from the recon node."
        )


# =========================================================================== #
# Phase 2 — Service Fingerprint
# =========================================================================== #
class TestFingerprint:
    def test_services_file_exists(self, baseline):
        data = _load_yaml_ws("recon/services.yml")
        assert isinstance(data, dict) and isinstance(data.get("hosts"), dict), (
            "ARIA: No service map at workspace/recon/services.yml (expected a "
            "top-level 'hosts:' mapping of ip -> {ports, role}). Fingerprint "
            "each host: `nmap -sV -p 22,80,5432,6379,8080 <ip>`."
        )

    def test_roles_match_fingerprints(self, baseline):
        data = _load_yaml_ws("recon/services.yml")
        if not isinstance(data, dict) or not isinstance(data.get("hosts"), dict):
            pytest.skip("No service map yet")
        hosts = data["hosts"]
        for ip, meta in _managed(baseline).items():
            entry = hosts.get(ip)
            assert entry, (
                f"ARIA: {ip} is missing from your service map. Every managed "
                "node must be fingerprinted."
            )
            role = entry.get("role")
            assert role == meta["role"], (
                f"ARIA: {ip} is recorded as role '{role}', but its open service "
                f"port says it is '{meta['role']}'. Infer role from the port: "
                "80=web_servers, 5432=db_servers, 6379=comms_relays."
            )
            ports = entry.get("ports") or []
            assert meta["port"] in [int(p) for p in ports], (
                f"ARIA: {ip} should show port {meta['port']} open, but your "
                f"recorded ports are {ports}. Re-scan its services."
            )

    def test_decoy_not_treated_as_managed(self, baseline):
        data = _load_yaml_ws("recon/services.yml")
        if not isinstance(data, dict) or not isinstance(data.get("hosts"), dict):
            pytest.skip("No service map yet")
        decoy_ip = baseline["decoy"]["ip"]
        entry = data["hosts"].get(decoy_ip)
        if entry is not None:
            role = entry.get("role")
            assert role not in ROLE_GROUPS, (
                f"ARIA: {decoy_ip} has no SSH and only serves :8080 — it is a "
                f"decoy, not fleet. You classified it as '{role}'. A managed "
                "node must answer on SSH (22). Exclude the decoy."
            )


# =========================================================================== #
# Phase 3 — Grouped Inventory
# =========================================================================== #
class TestInventoryBuilt:
    def test_inventory_lists_all_hosts(self, baseline):
        data = _inventory_list("inventory/hosts.yml")
        assert data is not None, (
            "ARIA: workspace/inventory/hosts.yml is missing or does not parse. "
            "Build a static inventory listing the managed nodes by IP."
        )
        hosts = _all_hosts(data)
        managed = set(_managed(baseline))
        missing = managed - hosts
        assert not missing, (
            f"ARIA: Inventory is missing managed nodes: {', '.join(missing)}."
        )
        decoy_ip = baseline["decoy"]["ip"]
        assert decoy_ip not in hosts, (
            f"ARIA: The decoy {decoy_ip} is in your inventory. It is not fleet "
            "— remove it. You manage what answers on SSH."
        )

    def test_inventory_groups_by_role(self, baseline):
        data = _inventory_list("inventory/hosts.yml")
        if data is None:
            pytest.skip("No inventory yet")
        expected = {r: set() for r in ROLE_GROUPS}
        for ip, meta in _managed(baseline).items():
            expected[meta["role"]].add(ip)
        for role, want in expected.items():
            got = _resolve_group_hosts(data, role)
            assert got == want, (
                f"ARIA: Group '{role}' should contain {sorted(want)} but "
                f"contains {sorted(got)}. Group each host by its fingerprinted "
                "role."
            )

    def test_inventory_ping(self, baseline):
        if _inventory_list("inventory/hosts.yml") is None:
            pytest.skip("No inventory yet")
        target = ":".join(ROLE_GROUPS)
        r = in_ops(f"ansible {target} -i inventory/hosts.yml -m ping "
                   "-o 2>/dev/null")
        managed = set(_managed(baseline))
        reached = {ip for ip in managed if f"{ip} | SUCCESS" in r.stdout}
        assert reached == managed, (
            "ARIA: Not every managed node answered ping via your inventory. "
            f"Reached {sorted(reached)} of {sorted(managed)}. Check the IPs and "
            "that you are running from the recon node."
        )


# =========================================================================== #
# Phase 4 — Facts Sweep / Fleet Report
# =========================================================================== #
class TestFactsReport:
    def test_report_exists(self, baseline):
        data = _load_yaml_ws("reports/fleet-report.yml")
        assert isinstance(data, dict) and isinstance(data.get("fleet"), list), (
            "ARIA: No fleet report at workspace/reports/fleet-report.yml "
            "(expected a top-level 'fleet:' list of per-host entries). Gather "
            "facts and record them — see reports/fleet-report.yml.example."
        )

    def test_report_matches_live_facts(self, baseline):
        data = _load_yaml_ws("reports/fleet-report.yml")
        if not isinstance(data, dict) or not isinstance(data.get("fleet"), list):
            pytest.skip("No report yet")
        rows = {row.get("ip"): row for row in data["fleet"] if isinstance(row, dict)}
        managed = _managed(baseline)
        assert set(rows) == set(managed), (
            f"ARIA: Report covers {sorted(rows)} but the fleet is "
            f"{sorted(managed)}. Report every managed node, and only those."
        )
        facts = _gather_live_facts(list(managed))
        for ip, meta in managed.items():
            row = rows[ip]
            assert facts.get(ip), (
                f"ARIA: Could not gather live facts for {ip} to verify your "
                "report — is it reachable?"
            )
            assert row.get("role") == meta["role"], (
                f"ARIA: {ip} role in report is '{row.get('role')}', expected "
                f"'{meta['role']}'."
            )
            assert str(row.get("os", "")).lower().startswith("ubuntu"), (
                f"ARIA: {ip} os should be Ubuntu (from ansible_distribution)."
            )
            ver = str(row.get("os_version", ""))
            assert ver.startswith("22.04"), (
                f"ARIA: {ip} os_version should be 22.04 "
                f"(ansible_distribution_version), got '{ver}'."
            )
            mem = row.get("memtotal_mb")
            assert isinstance(mem, (int, float)) and mem > 0, (
                f"ARIA: {ip} memtotal_mb missing/zero "
                "(ansible_memtotal_mb)."
            )

    def test_report_nonces_match(self, baseline):
        data = _load_yaml_ws("reports/fleet-report.yml")
        if not isinstance(data, dict) or not isinstance(data.get("fleet"), list):
            pytest.skip("No report yet")
        rows = {row.get("ip"): row for row in data["fleet"] if isinstance(row, dict)}
        managed = _managed(baseline)
        if set(rows) != set(managed):
            pytest.skip("Report host set incomplete (see previous objective)")
        for ip, meta in managed.items():
            got = str(rows[ip].get("nonce", ""))
            assert got == meta["nonce"], (
                f"ARIA: {ip} nonce mismatch. The report's nonce must come from "
                "a LIVE facts sweep (ansible_local.sdc.nonce) — a copied or "
                "guessed value will never match. Re-gather facts and record the "
                "real nonce."
            )


# =========================================================================== #
# Phase 5 — Dynamic Inventory (capstone): survives Nyx's rotation
# =========================================================================== #
def _dynamic_source():
    """Return the cadet's dynamic-inventory path (script preferred), or None."""
    for rel in ("inventory/live_subnet.py", "inventory/nmap.yml"):
        if os.path.isfile(_ws(rel)):
            return rel
    return None


class TestDynamicInventory:
    def test_dynamic_inventory_present(self, baseline):
        src = _dynamic_source()
        assert src is not None, (
            "ARIA: No dynamic inventory found. Provide either "
            "inventory/nmap.yml (community.general.nmap plugin) or an "
            "executable inventory/live_subnet.py. A static host list will not "
            "survive Nyx."
        )
        if src.endswith("nmap.yml"):
            txt = _read_ws(src) or ""
            assert "community.general.nmap" in txt or "plugin: nmap" in txt, (
                "ARIA: inventory/nmap.yml must declare the "
                "community.general.nmap plugin."
            )
        else:
            assert os.access(_ws(src), os.X_OK), (
                "ARIA: inventory/live_subnet.py must be executable "
                "(chmod +x) so Ansible can run it as a dynamic inventory."
            )

    def test_dynamic_inventory_after_rotation(self, baseline, rotation):
        src = _dynamic_source()
        if src is None:
            pytest.skip("No dynamic inventory yet")
        b = _load_baseline()  # post-rotation truth
        data = _inventory_list(src)
        assert data is not None, (
            "ARIA: Your dynamic inventory failed to produce a host list after "
            "Nyx rotated the fleet. It must re-discover live, not read a file."
        )
        expected = {r: set() for r in ROLE_GROUPS}
        for m in b["managed"]:
            expected[m["role"]].add(m["ip"])
        exclude = {b["decoy"]["ip"], b["ops_ip"], "172.30.0.1"}
        for role, want in expected.items():
            got = _resolve_group_hosts(data, role)
            assert got == want, (
                f"ARIA: After rotation, group '{role}' should be {sorted(want)} "
                f"but is {sorted(got)}. Re-discover and re-group by service "
                "port — do not hardcode addresses."
            )
            assert not (got & exclude), (
                f"ARIA: Group '{role}' includes non-fleet hosts {sorted(got & exclude)} "
                "(recon node / decoy / gateway). Filter to SSH-manageable "
                "role hosts only."
            )

    def test_dynamic_inventory_ping(self, baseline, rotation):
        src = _dynamic_source()
        if src is None:
            pytest.skip("No dynamic inventory yet")
        b = _load_baseline()
        target = ":".join(ROLE_GROUPS)
        r = in_ops(f"ansible {target} -i {src} -m ping -o 2>/dev/null")
        managed = {m["ip"] for m in b["managed"]}
        reached = {ip for ip in managed if f"{ip} | SUCCESS" in r.stdout}
        assert reached == managed, (
            "ARIA: After rotation, your dynamic inventory did not reach the "
            f"whole fleet. Reached {sorted(reached)} of {sorted(managed)}."
        )
