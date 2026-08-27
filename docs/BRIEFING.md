---
CLASSIFICATION: CADET EYES ONLY
MISSION: 1.6 — INVENTORY FROM NOTHING
THEATRE: Starfall Defence Corps Academy
AUTHORITY: SDC Cyber Command, 2187
---

# OPERATION ORDER — MISSION 1.6: INVENTORY FROM NOTHING

---

## 1. SITUATION

### 1a. Enemy Forces

Voidborn operative **NYX, THE SIGNAL GHOST** operates against fleet visibility
directly: she rotates network addressing on the fleet's nodes, so that any
static map of the fleet goes stale without warning. Nyx does not hide behind
firewalls or false credentials — she wins by making sure nothing responders
write down stays true for long. A hostname is not evidence. An IP address
written once is a liability.

### 1b. Friendly Forces

Every asset registry the Corps has built until now started from a handed-down
host list. That has never been how real incidents begin. This time Command is
withholding it deliberately: you receive **one authorised fact** — a subnet —
and nothing else. If the fleet cannot be found from a subnet alone, it cannot
be found at all once Nyx starts moving it.

### 1c. Attachments / Support

**ARIA** (Automated Review & Intelligence Analyst) is assigned to this
mission. ARIA holds independent ground truth on the range and will verify
your work by re-deriving it herself — not by trusting your files.

### 1d. Operational Tool

All operations will be conducted using **ANSIBLE** — *Automated Network for
Secure Infrastructure, Baseline Lockdown & Enforcement* — paired with `nmap`
for discovery. Both run from the recon node, `sdc-ops`. Nothing in this
mission is reachable from outside the range network.

---

## 2. MISSION

Discover the fleet hiding on `172.30.0.0/24`. Fingerprint every live host by
its open service port to determine role. Build a grouped Ansible inventory.
Sweep confirmed facts from every managed node into a fleet report. Then build
a **dynamic** inventory that re-discovers the fleet on every run, so that when
Nyx rotates addressing, your map does not go dark.

**End state**: A verified static inventory covering every managed node, a
facts-backed fleet report proving live contact, and a dynamic inventory that
survives a live rotation.

---

## 3. EXECUTION

### 3a. Commander's Intent

An inventory that only works once is not an inventory — it is a photograph.
This mission tests whether you can rebuild fleet visibility from raw network
access alone, and whether what you build keeps working after the ground shifts
under it. That second requirement is the whole point of Nyx: any cadet can
write down IPs they were told. Only a cadet who understands *how* those IPs
were found can re-find them.

### 3b. Concept of Operations

Five sequential phases. Complete each phase before advancing. Full procedural
detail is in **EXERCISES.md**.

| Phase | Task | Objective |
|-------|------|-----------|
| 1 | Recon Sweep | Discover every live host on the authorised subnet |
| 2 | Service Fingerprint | Determine each live host's role from its open service port |
| 3 | Grouped Inventory | Build a static Ansible inventory, grouped by role, and verify connectivity |
| 4 | Facts Sweep / Fleet Report | Gather live facts from every managed node and record a fleet report |
| 5 | Dynamic Inventory (capstone) | Build a discovery-based inventory that survives Nyx's IP rotation |

### 3c. Theatre of Operations

You are issued exactly one fact:

| Designation | Value |
|-------------|-------|
| Authorised training subnet | `172.30.0.0/24` |

Everything else — how many hosts, which IPs, which roles — is undocumented by
design. You will operate from the recon node `sdc-ops` (board it with
`make shell`); the managed fleet and the decoy expose no ports to your host
machine and are reachable only from inside the range network.

Hidden on the subnet: **three managed fleet nodes** and **one decoy**. Managed
nodes answer on SSH (port 22) plus one service port that reveals their role.
The decoy answers on port 8080 only and has **no SSH** — it is not fleet.
Container hostnames are opaque tokens; role can be determined **only** from
the open service port, never from the name.

**Port → role legend:**

| Open Port | Role |
|-----------|------|
| `80` | `web_servers` |
| `5432` | `db_servers` |
| `6379` | `comms_relays` |
| `8080` (no SSH) | decoy — not fleet, ignore it |

**SSH User**: `cadet`
**Authentication and connection defaults**: already configured in
`workspace/ansible.cfg`. You are not asked to write connection plumbing — you
are asked to find out *what* to point it at.

### 3d. Rules of Engagement

- This is a **defensive** mapping exercise conducted entirely inside the
  Academy's own authorised range. Discovery is confined to `172.30.0.0/24`.
- Do not hardcode any IP address you discover as a permanent assumption — Nyx
  is explicitly authorised to invalidate it. Your final deliverable must
  re-discover the fleet, not remember it.
- The decoy is a live host. It is not a target. A managed node is defined as
  one that answers SSH — nothing that fails that test belongs in your
  inventory.
- All findings must be reproducible. If ARIA cannot independently verify your
  work against the live range, your work is not complete.

---

## 4. SUPPORT

| Resource | Function | Command |
|----------|----------|---------|
| **ARIA** | Verifies mission compliance; reports pass/fail per phase | `make test` |
| **HINTS.md** | Operational guidance if the mission stalls | — |
| **Range Reset** | Rebuilds the recon node and fleet, re-randomises addressing | `make reset` |
| **Nyx Rotation Drill** | Forces an addressing rotation on demand, so you can watch a static inventory break | `make rotate` |

Run `make test` after each phase. Do not advance until ARIA confirms the phase
complete.

Consulting **HINTS.md** is authorised at Cadet rank. Using available
intelligence is not weakness — it is doctrine.

---

## 5. COMMAND AND SIGNAL

**Reporting**: ARIA is your automated reporting chain. Her output is your
after-action record. She never trusts your files alone — she re-derives the
truth from the live range and checks your work against it.

**Commander's Final Order**: This mission does not end until the fleet is
mapped from the subnet alone, the report is backed by live facts — not
guesses — and your inventory survives Nyx moving every address on the board.
No exceptions.

Proceed to **EXERCISES.md** for phase-by-phase operational instructions.

---

*SDC Cyber Command — 2187 — CADET EYES ONLY*
