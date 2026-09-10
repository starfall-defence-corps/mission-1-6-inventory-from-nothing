# Mission 1.6: Inventory from Nothing — Hints & Troubleshooting Guide

> 📚 Deeper reference: [FM-1 — Ansible Module Reference](https://github.com/starfall-defence-corps/sdc-academy/blob/main/field-manuals/FM-1-ansible-reference.md)

**Rank**: Sub-Lieutenant (Maximum Scaffolding)

This guide is your safety net. If something is not working, the answer is
likely here. Read the relevant section carefully before asking for help.
Hints below are ordered light → heavy — try the nudge first.

---

## Phase 1: Recon Sweep

**Nudge:** You're looking for a single `nmap` flag that discovers live hosts
without scanning their ports. Run it against the whole `/24`, from inside
`sdc-ops`.

**More:** `nmap -sn 172.30.0.0/24` needs `sudo` inside the container for raw
ARP scanning of the local segment. If you skip `sudo`, `nmap` falls back to a
slower method and may miss hosts entirely.

**Full solution:**

```bash
sudo nmap -sn 172.30.0.0/24 | grep -i up
```

`grep -i up` filters the scan report down to the "Host is up" lines paired
with each address, which is a fast way to eyeball what responded. Every
address that shows up here except `172.30.0.1` (gateway) and `172.30.0.10`
(your own `sdc-ops`) belongs in `workspace/recon/live-hosts.txt` — one IP per
line. At this stage you don't yet know which are fleet and which is the
decoy; that's Phase 2.

---

## Phase 2: Service Fingerprint

**Nudge:** You already know the five ports that matter:
`22, 80, 5432, 6379, 8080`. Scan each live host against exactly that list.

**More:** `-Pn` tells `nmap` to skip its own host-liveness check and scan
regardless — useful since you already confirmed liveness in Phase 1, and some
container network setups respond oddly to `nmap`'s default ping probe.

**Full solution:**

```bash
nmap -Pn -p 22,80,5432,6379,8080 <ip>
```

Run this once per host from Phase 1. Read the "PORT / STATE" table in the
output and map whichever role port is `open` to a role:

| Open Port | Role |
|-----------|------|
| `80` | `web_servers` |
| `5432` | `db_servers` |
| `6379` | `comms_relays` |

If `22/tcp` is **not** open on a host, it cannot be a managed node no matter
what else is open — that's the decoy. Mark it `role: unmanaged` (or omit it)
in `workspace/recon/services.yml`, never under one of the three role names.

---

## Phase 3: Grouped Inventory

**Nudge:** You don't need to write any connection settings — user, key, and
host-key-checking are already handled in `workspace/ansible.cfg`. You only
need to list hosts, grouped by role.

**More:** Groups nest under `all: children:`. A parent `fleet` group wrapping
the three role groups is optional but convenient — it lets you write
`ansible fleet -m ping` instead of listing all three group names.

**Full solution** — a sample grouped `workspace/inventory/hosts.yml`:

```yaml
all:
  children:
    fleet:
      children:
        web_servers:
          hosts:
            172.30.0.42: {}
        db_servers:
          hosts:
            172.30.0.87: {}
        comms_relays:
          hosts:
            172.30.0.130: {}
```

Substitute the real IPs you fingerprinted in Phase 2 — these are examples
only, and yours will be different every time you `make setup`. The decoy's
IP must never appear in this file. Verify with:

```bash
ansible web_servers:db_servers:comms_relays -m ping
```

If a host comes back `UNREACHABLE`, the most common cause is a stale IP —
addressing is re-randomised on every `make setup`/`make reset`. Re-check your
Phase 1/2 findings against what's currently live.

---

## Phase 4: Facts Sweep / Fleet Report

**Nudge:** Everything in the report comes from one command:
`ansible web_servers:db_servers:comms_relays -m setup`. Don't type any value
you didn't see in that output.

**More:** The nonce is not a top-level fact — it's nested under
`ansible_local.sdc.nonce`, because it's an Ansible **local fact** (planted on
the node, not derived from hardware/OS state). If you filter the `setup`
output, make sure your filter is broad enough to include `ansible_local`, or
just look at the unfiltered output.

**Full solution:**

```bash
ansible web_servers:db_servers:comms_relays -m setup
```

For each host, pull these five values out of the JSON and write them into
`workspace/reports/fleet-report.yml` (start from
`reports/fleet-report.yml.example`):

| Report Field | Where It Comes From |
|---------------|---------------------|
| `hostname` | `ansible_facts.ansible_hostname` |
| `os` | `ansible_facts.ansible_distribution` → `Ubuntu` |
| `os_version` | `ansible_facts.ansible_distribution_version` → `22.04` |
| `memtotal_mb` | `ansible_facts.ansible_memtotal_mb` |
| `nonce` | `ansible_facts.ansible_local.sdc.nonce` |

**Why the nonce matters:** it's regenerated every time the range is armed
(`make setup`, `make reset`, `make rotate`), and it's never written anywhere
in this repo. ARIA re-gathers it herself from the live nodes and compares —
so a value you guess, reuse from a previous run, or hardcode will never
match. The only way to get it right is to actually contact the node and read
its facts, which is precisely the property this phase is testing.

---

## Phase 5: Dynamic Inventory (Capstone)

**Nudge:** A dynamic inventory is just an executable file that prints JSON
when called with `--list`. Nothing stops that JSON from being computed live,
by scanning the subnet, instead of read from a file.

**More:** The classification rule is exactly your Phase 2 logic, just
automated: a host counts as fleet only if `22/tcp` is open (excludes the
decoy) **and** exactly one of `80`/`5432`/`6379` is open (excludes the gateway
and `sdc-ops`, which don't run any role service). Group by whichever port
matched.

**Full worked solution** — this is the verified reference answer. Save it as
`workspace/inventory/live_subnet.py` and `chmod +x` it:

```python
#!/usr/bin/env python3
"""live_subnet — dynamic inventory: scan the subnet, keep SSH-manageable role
hosts, group by role. Survives IP rotation because it re-discovers each run."""
import concurrent.futures, json, socket, sys
SUBNET_PREFIX = "172.30.0."
HOST_RANGE = range(2, 255)
ROLE_BY_PORT = {80: "web_servers", 5432: "db_servers", 6379: "comms_relays"}
def _open(ip, port, timeout=0.4):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(timeout)
    try: s.connect((ip, port)); return True
    except OSError: return False
    finally: s.close()
def _classify(ip):
    if not _open(ip, 22): return None            # must be SSH-manageable (skips the decoy)
    for port, role in ROLE_BY_PORT.items():
        if _open(ip, port): return ip, role      # role from the open service port
    return None                                  # no role service (skips recon node/gateway)
def build():
    inv = {"_meta": {"hostvars": {}}}
    groups = {r: {"hosts": []} for r in ROLE_BY_PORT.values()}
    ips = [f"{SUBNET_PREFIX}{o}" for o in HOST_RANGE]
    with concurrent.futures.ThreadPoolExecutor(max_workers=64) as ex:
        for res in ex.map(_classify, ips):
            if res: ip, role = res; groups[role]["hosts"].append(ip)
    for role, g in groups.items(): g["hosts"].sort(); inv[role] = g
    inv["fleet"] = {"children": list(ROLE_BY_PORT.values())}
    return inv
if __name__ == "__main__":
    print(json.dumps({} if "--host" in sys.argv else build(), indent=2))
```

**Reading the script:**

- `_open(ip, port)` is a raw TCP connect probe with a short timeout — it does
  not need `nmap` or root, just a socket connection attempt per port.
- `_classify(ip)` enforces the two-part rule from Phase 2: must have SSH open,
  must have exactly one role port open. Everything else returns `None` and is
  dropped — this is what silently excludes the gateway, `sdc-ops`, and the
  decoy without you having to special-case any of their addresses.
- `ThreadPoolExecutor(max_workers=64)` scans all 253 candidate addresses in
  parallel, so the whole sweep finishes in well under a second instead of
  253 sequential connection timeouts.
- `build()` returns a dict shaped exactly like `ansible-inventory --list`
  output: role groups with a `hosts` list, plus a `fleet` parent group of
  `children`. There is no `_meta.hostvars` content needed because the group
  membership alone is enough — connection settings still come from
  `ansible.cfg`.
- The `--host` branch exists because Ansible's dynamic-inventory contract
  calls scripts with `--list` for the whole inventory and (historically)
  `--host <name>` for a single host's vars; returning `{}` there is correct
  since all our host data lives in `_meta` / the group lists already.

Verify it, including after a forced rotation:

```bash
chmod +x inventory/live_subnet.py
ansible-inventory -i inventory/live_subnet.py --list
ansible web_servers:db_servers:comms_relays -i inventory/live_subnet.py -m ping
```

Then, from the project root, `make rotate` and re-run the two commands above
from inside `sdc-ops` — a correct script finds the fleet at its new addresses
without any code change.

---

## Connection Hints

**"Connection refused" / can't reach any host at all**
Make sure you are running `nmap` and `ansible` **from inside `sdc-ops`**
(`make shell`), not from your host machine. The fleet and the decoy publish
no ports to the host — they are only reachable from inside the range
network.

**"No route to host" / everything times out**
Confirm the range is actually up: from the project root, `docker ps` should
show `sdc-ops` plus three fleet containers plus a decoy container, all `Up`.
If not, `make setup` (or `make reset` for a clean rebuild).

**"Permission denied (publickey)"**
`make setup` places the cadet SSH key inside `sdc-ops` automatically at
`/home/cadet/.ssh/cadet_key`, and `workspace/ansible.cfg` already points at
it. If you're hitting this, first confirm you're running Ansible from inside
`sdc-ops` and not from your host — the key isn't present there.

**"Host key verification failed"**
`workspace/ansible.cfg` already disables strict host-key checking for this
range. This error usually means you're running Ansible from somewhere other
than `~/workspace` inside `sdc-ops`, so it isn't picking up that config.

**My IPs from last session don't work anymore**
That's expected, not a bug. Addressing is randomised on every `make setup` /
`make reset`, and can also change mid-session via `make rotate`. Re-sweep
rather than reusing old values — this is the entire premise of the mission.

---

## Ad-hoc Command Hints

**The two most important flags:**
- `-m` specifies the **module**: `-m ping`, `-m setup`
- `-i` specifies the **inventory source**: `-i inventory/hosts.yml` or
  `-i inventory/live_subnet.py` (defaults to `inventory/hosts.yml` per
  `ansible.cfg` if omitted)

**The `ping` module is not ICMP ping.**
It does not send network pings. It tests whether Ansible can connect to the
host, authenticate, and run Python. A `pong` response means full Ansible
connectivity is confirmed.

**Targeting hosts and groups:**
```
ansible fleet -m ping                                  # if you built a parent 'fleet' group
ansible web_servers:db_servers:comms_relays -m ping     # union of the three role groups, always works
ansible web_servers -m ping                              # target only one role group
```

---

## General Troubleshooting

**If everything is broken and you are not sure where to start:**
```bash
make reset
```
This rebuilds the entire range from scratch and re-randomises addressing.
You will not lose your files in `workspace/` — only the containers and the
network state are reset.

**"make: *** No targets specified" or "make: *** No rule to make target"**
You are in the wrong directory. `make` commands run from the project root
where the `Makefile` lives — not from inside `sdc-ops`. If you're inside the
recon-node shell, `exit` first, or open a second terminal at the project
root.

**If `make test` fails:**
Read ARIA's error message carefully — she tells you specifically what she
expected versus what she found on the live range, not just "wrong file".
Fix that one thing, then run `make test` again.

**Check container status at any time (from the project root):**
```bash
docker ps
```
You should see `sdc-ops` plus the (opaquely-named) fleet and decoy
containers, all `Up`.

**Quick diagnostic sequence when something is not working:**
1. `docker ps` (project root) — is the range running?
2. `make shell` — can you board `sdc-ops`?
3. `sudo nmap -sn 172.30.0.0/24` (inside `sdc-ops`) — is the subnet actually
   reachable from here?
4. `ansible web_servers:db_servers:comms_relays -m ping` — does your
   inventory reach what you found?
