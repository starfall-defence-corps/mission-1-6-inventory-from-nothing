# Mission 1.6: Inventory from Nothing — Progress Tracker

**Rank**: Sub-Lieutenant
**Mission Progress**: 6 of 6 toward Sub-Lieutenant

Check each item off as you complete it. If a phase is blocked, see
`docs/HINTS.md`.

---

## Phase 0: Power Up the Range

- [ ] `make doctor` passes
- [ ] `make setup` reports "Range ONLINE" with the authorised subnet
- [ ] `make shell` boards the recon node (`sdc-ops`) into `~/workspace`

---

## Phase 1: Recon Sweep

- [ ] Deliverable: `workspace/recon/live-hosts.txt` — one IP per line
- [ ] Verify: `sudo nmap -sn 172.30.0.0/24` (from inside `sdc-ops`)
- [ ] Gateway (`172.30.0.1`) and recon node (`172.30.0.10`) excluded

---

## Phase 2: Service Fingerprint

- [ ] Deliverable: `workspace/recon/services.yml` — top-level `hosts:` map of `ip -> {ports, role}`
- [ ] Verify: `nmap -sV -p 22,80,5432,6379,8080 <ip>` per discovered host
- [ ] Every managed node's role inferred from its open service port (`80`/`5432`/`6379`)
- [ ] Decoy (port `8080`, no SSH) recorded as `unmanaged` — never as a fleet role

---

## Phase 3: Grouped Inventory

- [ ] Deliverable: `workspace/inventory/hosts.yml`
- [ ] All 3 managed nodes listed by IP, grouped into `web_servers` / `db_servers` / `comms_relays`
- [ ] Decoy is **not** present anywhere in the inventory
- [ ] Verify: `ansible web_servers:db_servers:comms_relays -m ping` — SUCCESS for all three

---

## Phase 4: Facts Sweep / Fleet Report

- [ ] Deliverable: `workspace/reports/fleet-report.yml` — top-level `fleet:` list
- [ ] Verify: `ansible web_servers:db_servers:comms_relays -m setup`
- [ ] Every entry has `ip`, `hostname`, `role`, `os`, `os_version`, `memtotal_mb`, `nonce`
- [ ] Every value comes from a **live** facts sweep — nonce from `ansible_local.sdc.nonce`

---

## Phase 5: Dynamic Inventory (Capstone)

- [ ] Deliverable: `workspace/inventory/live_subnet.py` — executable (`chmod +x`)
- [ ] Verify: `ansible-inventory -i inventory/live_subnet.py --list`
- [ ] Verify: `ansible web_servers:db_servers:comms_relays -i inventory/live_subnet.py -m ping`
- [ ] Survives rotation: after `make rotate`, the dynamic inventory still finds all 3 managed nodes, correctly grouped, excluding the recon node/decoy/gateway

---

## Before You Submit

- [ ] `make test` — all ARIA checks pass
- [ ] `make submit` — branch, commit, push, open PR

**Next stop**: [Gateway Simulation — Operation: First Contact](https://github.com/starfall-defence-corps/gateway-simulation)
