# Starfall Defence Corps Academy

> 🧭 [← 1.5 Clean House](https://github.com/starfall-defence-corps/mission-1-5-clean-house) · **You are here: 1.6 Inventory from Nothing** · [Gateway Simulation →](https://github.com/starfall-defence-corps/gateway-simulation) · [🏠 Academy Hub](https://github.com/starfall-defence-corps/sdc-academy)

> ☁️ **No Docker on your machine?** Create your own copy first (Use this template), then on **your** repo: **Code → Codespaces → Create codespace** — everything is preinstalled. First boot takes ~5 min (one-time); after that it starts fast.

## Mission 1.6: Inventory from Nothing

> *"Nyx doesn't hide the fleet. She just makes sure it never sits still long enough for you to write it down."*

Every prior mission handed you a host list. Not this one. **Nyx, the Signal Ghost** rotates fleet addressing to blind responders, and this time you start with exactly one fact: a subnet, `172.30.0.0/24`. Somewhere on it are three fleet nodes and one decoy. No hostnames, no ports on a table, no map. You board the recon node, sweep the range, fingerprint what you find, and build the inventory yourself — static first, then a dynamic one that survives Nyx moving the furniture. This is the last Foundation skill before Gateway: bootstrap a fleet map from nothing.

This is a purely **defensive** exercise. You are mapping infrastructure your own Academy range owns and has authorised you to map — nothing here touches a third party.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (with Docker Compose v2)
- [GNU Make](https://www.gnu.org/software/make/)
- Python 3.10+ (for the test environment) — on Debian/Ubuntu: `sudo apt install python3-venv`
- Git

> Ansible and `nmap` do **not** need to be installed on your machine for this mission — they run inside the recon node container. You only need Docker, Make, Python, and Git on the host.

> **Windows users**: run everything inside [WSL2](https://learn.microsoft.com/en-us/windows/wsl/install), with Docker Desktop on the WSL2 backend.

## Quick Start

```bash
# 1. Use this template on GitHub (green button, top right) to create YOUR OWN
#    copy. Set it Public, then clone it:
git clone https://github.com/YOUR-USERNAME/mission-1-6-inventory-from-nothing.git
cd mission-1-6-inventory-from-nothing

# 2. Check your machine is mission-ready
make doctor

# 3. Power up the range — recon node + hidden fleet + decoy
make setup

# 4. Board the recon node. This is where you run nmap and ansible.
make shell
```

5. **Read your orders**: [Mission Briefing](docs/BRIEFING.md)
6. **Work the phases**: [Exercises](docs/EXERCISES.md)
7. **Stuck?** [Hints & Troubleshooting](docs/HINTS.md)
8. **Track progress**: [Checklist](CHECKLIST.md)

You start with **one fact and nothing else: the subnet `172.30.0.0/24`.** IPs, hostnames, and roles are not written anywhere in this repo — you have to go find them.

## Lab Architecture

```
 Your Machine
+---------------------------------------------------------------+
|  workspace/           (the only place you write anything)      |
|    ansible.cfg                  (connection defaults, pre-wired)|
|    recon/live-hosts.txt         (you create — Phase 1)         |
|    recon/services.yml           (you create — Phase 2)         |
|    inventory/hosts.yml          (you create — Phase 3)         |
|    inventory/live_subnet.py     (you create — Phase 5)         |
|    reports/fleet-report.yml     (you create — Phase 4)         |
|                                                                 |
|  Docker Network: 172.30.0.0/24                                  |
|  +------------+                                                 |
|  | sdc-ops    |  recon / control node — board it with `make shell`
|  | .10  :2221 |  ansible + nmap live here                        |
|  +------------+                                                 |
|                                                                 |
|  hidden fleet — IPs randomised each `make setup`, no host ports  |
|  +------------+ +------------+ +------------+  +------------+   |
|  | sdc-????   | | sdc-????   | | sdc-????   |  | sdc-????   |   |
|  | :22, :80   | | :22, :5432 | | :22, :6379 |  | :8080 only |   |
|  | web_servers| | db_servers | | comms_relays| | DECOY, no SSH|  |
|  +------------+ +------------+ +------------+  +------------+   |
+---------------------------------------------------------------+
```

Opaque container hostnames (like `sdc-3f9a`) mean role can only be inferred
from the open service port — never from the name. All discovery happens
**from inside `sdc-ops`**: the fleet and the decoy publish no ports to your
host, so `make shell` is where the mission lives.

## Available Commands

```
make help       Show available commands
make doctor     Check your machine is mission-ready
make setup      Power up the range (recon node + hidden fleet)
make shell      Board the recon node (sdc-ops) — run nmap + ansible from here
make test       Ask ARIA to verify your work
make rotate     (advanced) Force Nyx to rotate the fleet's addressing now
make submit     Submit your work for ARIA review (branch, commit, push, PR)
make reset      Tear down and rebuild the range (re-randomises addressing)
make destroy    Tear down everything (containers, keys, range state, venv)
```

## Mission Files

| File | Purpose |
|------|---------|
| [BRIEFING.md](docs/BRIEFING.md) | Mission briefing — **read this first** |
| [EXERCISES.md](docs/EXERCISES.md) | Phase-by-phase operational instructions (5 phases) |
| [HINTS.md](docs/HINTS.md) | Troubleshooting and hints |
| [CHECKLIST.md](CHECKLIST.md) | Progress tracker |

## ARIA Review (Pull Request Workflow)

**ARIA** (Automated Review & Intelligence Analyst) reviews your work two ways:

**Locally** — run `make test` for instant pass/fail verification. No API key needed.

**On Pull Request** — run `make submit` (or push a branch and open a PR to `main`
manually), and ARIA posts a qualitative review as a PR comment. To enable it, add
an `ANTHROPIC_API_KEY` repo secret (**Settings → Secrets and variables → Actions**).
Without a key, PR review is skipped and `make test` still works locally.

## Troubleshooting

**Containers won't start**: Ensure Docker Desktop is running; check for port conflicts on 2221-2223 (only one SDC lab can run at a time — `make destroy` in any other mission first).

**Can't see any hosts on the subnet**: Make sure you are running `nmap` **from inside `sdc-ops`** (`make shell`), not from your host machine. The fleet publishes no ports to your host — it is only reachable from inside the range network.

**`make test` fails with "No module named pytest"**: run `make setup` first — it builds the Python environment.

**Need a clean slate, or the addressing feels stale**: `make reset` (rebuilds the range and re-randomises everything) or `make destroy` (full teardown).

**Docker network conflict** ("Pool overlaps..."): another Docker network is using 172.30.0.0/24 — stop it, or edit `.docker/docker-compose.yml`.
