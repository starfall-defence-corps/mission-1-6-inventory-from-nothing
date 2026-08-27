---
CLASSIFICATION: CADET EYES ONLY
MISSION: 1.6 — INVENTORY FROM NOTHING
DOCUMENT: EXERCISES — Phase-by-Phase Operational Instructions
---

# EXERCISES — MISSION 1.6: INVENTORY FROM NOTHING

Complete each phase in sequence. Run `make test` after each phase. Do not
advance until ARIA confirms compliance.

**Two places, two purposes:**

- **`make` commands** (`make setup`, `make shell`, `make test`, `make reset`):
  run from the **project root** on your host machine, where the `Makefile`
  lives.
- **Discovery and Ansible commands** (`nmap`, `ansible`, `ansible-playbook`):
  run from **inside the recon node**, `sdc-ops`, which you board with
  `make shell`. That drops you into `~/workspace` (bind-mounted to your
  project's `workspace/` directory) with `nmap` and `ansible` already
  installed. The fleet is not reachable from your host — only from inside the
  range network.

When a phase says "Run ARIA's Verification", open a **second terminal** at the
project root (or exit the recon-node shell with `exit`) and run `make test`
from there.

---

## PHASE 0: Power Up the Range

> Before any discovery can begin, the range must be online. This mission's
> range is different from prior missions: nothing is handed to you. Power it up
> and confirm your one authorised fact.

### Step 0.1 — Preflight Check

From the **project root**, run:

```bash
make doctor
```

ARIA checks Docker, ports 2221-2223, disk space, and your toolchain before you
spend time on a lab that cannot boot.

### Step 0.2 — Start the Range

```bash
make setup
```

This builds the recon node (`sdc-ops`), the hidden fleet, and the decoy;
generates SSH credentials; randomises fleet addressing; and arms each managed
node with its role service and a live attestation nonce. Wait for:

```
  Range ONLINE. You have ONE fact: the subnet.

    Authorized training subnet:  172.30.0.0/24
```

That subnet is genuinely everything you are given. IPs, hostnames, and roles
are not written anywhere in this repository — `make setup` randomises them
fresh every time, and they are gitignored.

### Step 0.3 — Board the Recon Node

```bash
make shell
```

This drops you into `sdc-ops` as the `cadet` user, inside `~/workspace`
(the same directory as your project's `workspace/` folder — anything you
create here appears on your host, and vice versa). All discovery and Ansible
commands in this mission are run **from this shell**, unless a step says
otherwise.

### Step 0.4 — If Things Go Wrong

If the range is in a bad state or you want a clean start, from the project
root:

```bash
make reset
```

This destroys and rebuilds the range and **re-randomises addressing** — a
clean start, not a checkpoint restore. Your files in `workspace/` are
preserved; only the containers and addressing are reset.

---

## PHASE 1: Recon Sweep

> You have a subnet and nothing else. Before you can build anything, you have
> to find out what is actually alive on `172.30.0.0/24`. Sweep it.

### What You Are Building

A plain list of every live IP address on the subnet, recorded at
`workspace/recon/live-hosts.txt` — one IP per line.

### Step 1.1 — Sweep the Subnet

From inside `sdc-ops` (`make shell`), in `~/workspace`:

```bash
sudo nmap -sn 172.30.0.0/24
```

**Command breakdown:**

| Part | Meaning |
|------|---------|
| `nmap` | Network mapper |
| `-sn` | Ping scan — discover live hosts, skip port scanning |
| `172.30.0.0/24` | The entire authorised subnet, all 254 usable addresses |

The output lists every address that answered, one block per host, with a
line like `Nmap scan report for 172.30.0.42`.

### Step 1.2 — Exclude What Is Not Fleet

Two addresses on this subnet are never fleet, and should not go in your file:

- `172.30.0.1` — the network gateway
- `172.30.0.10` — `sdc-ops`, your own recon node

Everything else that answered the sweep is worth recording — including the
decoy. You will sort out which of those are actually managed nodes in
Phase 2.

### Step 1.3 — Record the Live Hosts

Create `workspace/recon/live-hosts.txt` with one IP per line — every host
your sweep found, minus the gateway and your own node. For example:

```
172.30.0.42
172.30.0.87
172.30.0.130
172.30.0.201
```

(Your actual addresses will differ — they are randomised per `make setup`.)

### Step 1.4 — Run ARIA's Verification

From the **project root**, in a second terminal:

```bash
make test
```

ARIA confirms your sweep found every live managed node before you advance.

---

## PHASE 2: Service Fingerprint

> A live IP tells you nothing about what a host does. Nyx's fleet has no
> hostnames you can trust and no documentation. The only honest signal is
> which service port a host has open. Fingerprint every host you found.

### What You Are Building

A service map at `workspace/recon/services.yml` recording, for every live
host, which ports are open and what role that implies. A template ships at
`workspace/recon/services.yml.example` — copy it and fill it in:

```bash
cp recon/services.yml.example recon/services.yml
```

### Step 2.1 — Scan Each Host's Services

For each IP from Phase 1, scan the ports that matter for this mission:

```bash
nmap -sV -p 22,80,5432,6379,8080 <ip>
```

You can also scan every candidate at once by passing a comma-separated list
or a small inline target file to `nmap` — either approach is fine, as long as
you end up with an accurate open-port list per host.

**Command breakdown:**

| Part | Meaning |
|------|---------|
| `-sV` | Probe open ports to determine service/version |
| `-p 22,80,5432,6379,8080` | Only check these five ports — the ones that matter |

### Step 2.2 — Infer Role from Open Port

Use this legend — it is the entire logic of this phase:

| Open Port | Role |
|-----------|------|
| `80` | `web_servers` |
| `5432` | `db_servers` |
| `6379` | `comms_relays` |
| `8080`, with **no** `22` | decoy — not fleet |

A genuine fleet node always has SSH (`22`) open alongside exactly one role
port. A host with **only** `8080` open, and no SSH, is the decoy Nyx planted
to waste your time. Mark it `role: unmanaged` in your service map (or leave
it out entirely) — either is acceptable, but it must never be recorded under
`web_servers`, `db_servers`, or `comms_relays`.

### Step 2.3 — Fill In the Service Map

Edit `workspace/recon/services.yml`. The structure is a top-level `hosts:`
map, keyed by IP:

```yaml
hosts:
  172.30.0.42:
    ports: [22, 80]
    role: web_servers
  172.30.0.87:
    ports: [22, 5432]
    role: db_servers
  172.30.0.130:
    ports: [22, 6379]
    role: comms_relays
  172.30.0.201:
    ports: [8080]
    role: unmanaged      # decoy — no SSH
```

Record the ports you actually observed open on each host — not just the one
that determined its role.

### Step 2.4 — Run ARIA's Verification

```bash
make test
```

ARIA checks that every managed node is fingerprinted with the correct role
and that the decoy has **not** been recorded as fleet.

---

## PHASE 3: Grouped Inventory

> You now know what each live host is. Time to make that knowledge
> operational: a static Ansible inventory, grouped by role, that you can point
> real commands at.

### What You Are Building

A static inventory at `workspace/inventory/hosts.yml`, listing only the
managed nodes (never the decoy), grouped into `web_servers`, `db_servers`,
and `comms_relays`.

### Step 3.1 — Understand What Is Already Wired

`workspace/ansible.cfg` already sets the SSH user (`cadet`), the private key,
and disables strict host-key checking for the range. You are not asked to
write any of that — only to build the host list itself.

### Step 3.2 — Build the Inventory

Using your Phase 2 service map, write `workspace/inventory/hosts.yml`. A
parent `fleet` group containing all three role groups is recommended (it
makes later commands easier to target), but the graded requirement is that
each managed node's IP appears under the correct role group. The **decoy must
not appear anywhere in this file.**

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

(Substitute your own discovered IPs — the ones above are examples.)

### Step 3.3 — Verify Connectivity

From inside `sdc-ops`, in `~/workspace`:

```bash
ansible web_servers:db_servers:comms_relays -m ping
```

**Command breakdown:**

| Part | Meaning |
|------|---------|
| `web_servers:db_servers:comms_relays` | Target the union of all three role groups |
| `-m ping` | Ansible's `ping` module — confirms SSH + Python, not ICMP |

Every managed node should return `SUCCESS` with `"ping": "pong"`. If a host
is unreachable, re-check that its IP in `hosts.yml` matches what you actually
discovered — addressing is randomised per `make setup`, so do not reuse
IPs from a previous run or from these examples.

### Step 3.4 — Run ARIA's Verification

```bash
make test
```

ARIA independently pings every managed node through your inventory and
confirms the decoy was excluded.

---

## PHASE 4: Facts Sweep / Fleet Report

> A grouped inventory proves you know where the fleet is. ARIA now wants proof
> you actually reached it — not IPs you copied down, but facts gathered live
> from each node.

### What You Are Building

A fleet report at `workspace/reports/fleet-report.yml`, one entry per managed
node, built entirely from live-gathered Ansible facts. A template ships at
`workspace/reports/fleet-report.yml.example` — copy it and fill it in:

```bash
cp reports/fleet-report.yml.example reports/fleet-report.yml
```

### Step 4.1 — Gather Facts from the Fleet

From inside `sdc-ops`:

```bash
ansible web_servers:db_servers:comms_relays -m setup
```

This returns a large JSON block per host, nested under `ansible_facts`. You
need five values out of it for each node:

| Field in Report | Source Fact |
|------------------|-------------|
| `hostname` | `ansible_hostname` |
| `os` | `ansible_distribution` (will read `Ubuntu`) |
| `os_version` | `ansible_distribution_version` (will read `22.04`) |
| `memtotal_mb` | `ansible_memtotal_mb` |
| `nonce` | `ansible_local.sdc.nonce` |

### Step 4.2 — Understand the Nonce

Every managed node has a random value — the **nonce** — planted on it when
the range was armed. It is surfaced as an Ansible **local fact**, at
`ansible_local.sdc.nonce`, and it only exists inside `ansible_facts` when you
actually gather facts from the live host. It is not written anywhere in this
repository, and it changes every `make setup` (and every `make rotate`).

This is the whole point of the field: a nonce you invent or copy from
somewhere else will never match ARIA's record. The only way to get the real
value is to contact the live node and read its facts. If you filter the
`setup` output, make sure your filter includes `ansible_local` — it is easy
to miss because it is a nested structure rather than a flat variable.

### Step 4.3 — Fill In the Fleet Report

Edit `workspace/reports/fleet-report.yml`. The structure is a top-level
`fleet:` list, one entry per managed node:

```yaml
fleet:
  - ip: 172.30.0.42
    hostname: sdc-3f9a
    role: web_servers
    os: Ubuntu
    os_version: "22.04"
    memtotal_mb: 3944
    nonce: a1b2c3d4e5f60718
  - ip: 172.30.0.87
    hostname: sdc-9c02
    role: db_servers
    os: Ubuntu
    os_version: "22.04"
    memtotal_mb: 3944
    nonce: 0f1e2d3c4b5a6978
  - ip: 172.30.0.130
    hostname: sdc-77ab
    role: comms_relays
    os: Ubuntu
    os_version: "22.04"
    memtotal_mb: 3944
    nonce: 88aa99bb00cc11dd
```

Every value except `ip` and `role` must come from your live facts sweep —
do not hand-type a plausible-looking hostname or nonce.

### Step 4.4 — Run ARIA's Verification

```bash
make test
```

ARIA re-gathers facts from the live fleet herself and compares them against
your report field by field — including the nonce. A report that does not
match a fresh sweep will not pass, even if it looks complete.

---

## PHASE 5: Dynamic Inventory (Capstone)

> Nyx's whole strategy is to make static maps expire. A `hosts.yml` with
> hardcoded IPs works exactly once — the moment she rotates the fleet's
> addressing, it points at nothing. Your final deliverable does not remember
> the fleet. It re-finds it, every time it is asked.

### What You Are Building

An **executable dynamic inventory script** at `workspace/inventory/live_subnet.py`
that scans the subnet live on every invocation, keeps only hosts that are
SSH-manageable **and** expose a known role port, and groups them by role.
Because it re-discovers from scratch each run, it survives Nyx's rotation —
where `inventory/hosts.yml` would silently go stale.

### Step 5.1 — Why a Script, Not a File

Ansible does not require your inventory to be static data. Any executable
file that, when run with `--list`, prints valid inventory JSON on stdout, can
serve as a dynamic inventory source. That means the inventory can contain
*logic* — including "go scan the network right now and report what's there."

### Step 5.2 — Write the Script

Create `workspace/inventory/live_subnet.py`. It needs to:

1. Enumerate every candidate address on `172.30.0.0/24`.
2. For each address, check whether SSH (port 22) is open. If not, discard it
   — this is what excludes the decoy.
3. For addresses that pass, check which role port (`80`, `5432`, `6379`) is
   open, and group the host under the matching role name.
4. Print the resulting inventory as JSON when called with `--list`.

### Step 5.3 — Make It Executable

```bash
chmod +x inventory/live_subnet.py
```

Ansible invokes dynamic inventory scripts directly, so the execute bit must
be set — without it, Ansible cannot run the script at all.

### Step 5.4 — Verify It

Confirm it produces a valid inventory:

```bash
ansible-inventory -i inventory/live_subnet.py --list
```

Then confirm Ansible can actually use it to reach the fleet:

```bash
ansible web_servers:db_servers:comms_relays -i inventory/live_subnet.py -m ping
```

Every managed node should return `SUCCESS` — with **no `hosts.yml` involved
at all**.

### Step 5.5 — Prove It Survives Rotation

This is the real test of the capstone. From the **project root** (a second
terminal, outside `sdc-ops`):

```bash
make rotate
```

This forces Nyx to move every managed node to a new address immediately, live
— no restart, no downtime, addressing only. Your Phase 3 `hosts.yml` now
points at dead IPs and will fail to reach the fleet. Back inside `sdc-ops`,
re-run:

```bash
ansible-inventory -i inventory/live_subnet.py --list
ansible web_servers:db_servers:comms_relays -i inventory/live_subnet.py -m ping
```

If your script is genuinely re-discovering rather than caching anything, it
should find the fleet at its **new** addresses without you touching a single
line of code.

### Step 5.6 — Optional Further Reading

Ansible ships a `community.general.nmap` inventory plugin that can perform
similar live-discovery through a YAML plugin configuration instead of a
Python script. It is worth knowing about (`workspace/ansible.cfg` already
enables it), but the executable script above is the recommended path for this
mission and is what ARIA's worked solution uses.

### Step 5.7 — Final ARIA Verification

```bash
make test
```

ARIA rotates the fleet herself and checks that your dynamic inventory
re-finds all three managed nodes, correctly grouped by role, excluding the
recon node, the decoy, and the gateway — every time, not just once.

---

## MISSION COMPLETE — DEBRIEF CHECKLIST

Before closing this mission, confirm the following:

- [ ] `workspace/recon/live-hosts.txt` lists every live host found on the sweep
- [ ] `workspace/recon/services.yml` fingerprints every managed node by role, and excludes the decoy
- [ ] `workspace/inventory/hosts.yml` groups all three managed nodes by role, with no decoy present
- [ ] `ansible web_servers:db_servers:comms_relays -m ping` succeeds against your static inventory
- [ ] `workspace/reports/fleet-report.yml` is filled in entirely from a live facts sweep, nonce included
- [ ] `workspace/inventory/live_subnet.py` exists, is executable, and re-discovers the fleet on every run
- [ ] Your dynamic inventory still reaches the whole fleet after `make rotate`
- [ ] `make test` reports all phases passing

If any item is incomplete, return to the corresponding phase and complete it
before closing the mission record.

---

*SDC Cyber Command — 2187 — CADET EYES ONLY*
