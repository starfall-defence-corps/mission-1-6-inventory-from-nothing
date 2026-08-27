#!/usr/bin/env bash
# =============================================================================
# setup-lab.sh — Mission 1.6 "Inventory from Nothing"
#
# Brings up the recon node (sdc-ops) plus three managed targets and one decoy,
# with RANDOMISED IPs + opaque hostnames written to a gitignored .docker/.env
# (so the answer never lives in the repo). Then it arms the range: starts each
# role's service-banner listener, injects a per-host nonce as an Ansible local
# fact (retrievable ONLY via a live facts sweep), and records the ground-truth
# .lab/baseline.json the grader reads.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$ROOT_DIR/.docker"
SSH_DIR="$DOCKER_DIR/ssh-keys"
ENV_FILE="$DOCKER_DIR/.env"
LAB_DIR="$ROOT_DIR/.lab"
COMPOSE=(docker compose -f "$DOCKER_DIR/docker-compose.yml" --env-file "$ENV_FILE")

# node container -> "role:port"
declare -a NODES=(sdc-node-a sdc-node-b sdc-node-c)
role_of() { case "$1" in
    sdc-node-a) echo "web_servers:80" ;;
    sdc-node-b) echo "db_servers:5432" ;;
    sdc-node-c) echo "comms_relays:6379" ;;
esac; }

echo ""
echo "=============================================="
echo "  STARFALL DEFENCE CORPS ACADEMY"
echo "  Mission 1.6 — Inventory from Nothing"
echo "  Powering up the range..."
echo "=============================================="
echo ""

# -- Host-side Python env (grader: pytest + aria-reporter) --------------------
if ! python3 -m venv --help &>/dev/null; then
    echo "  ERROR: python3-venv is not installed (apt install python3-venv)."; exit 1
fi
if [ ! -d "$ROOT_DIR/venv" ]; then
    echo "  Setting up Python environment..."
    python3 -m venv "$ROOT_DIR/venv"
    "$ROOT_DIR/venv/bin/pip" install -q -r "$ROOT_DIR/requirements.txt"
    echo "  Python environment ready."; echo ""
fi

# -- SSH credentials for the fleet --------------------------------------------
if [ ! -f "$SSH_DIR/cadet_key" ]; then
    echo "  Generating SSH credentials..."
    mkdir -p "$SSH_DIR"
    ssh-keygen -t ed25519 -f "$SSH_DIR/cadet_key" -N "" -C "cadet@starfall-academy" -q
    cp "$SSH_DIR/cadet_key.pub" "$SSH_DIR/authorized_keys"
    chmod 600 "$SSH_DIR/cadet_key"; chmod 644 "$SSH_DIR/authorized_keys"
fi

# -- Randomise the target/decoy addressing (the hidden answer) -----------------
# Four distinct host octets in .20-.240, avoiding .1 (gateway) and .10 (ops).
echo "  Assigning fleet addressing (randomised)..."
python3 - "$ENV_FILE" <<'PY'
import random, sys
env_path = sys.argv[1]
pool = [o for o in range(20, 241)]
random.shuffle(pool)
a, b, c, d = pool[0], pool[1], pool[2], pool[3]
def tok(): return "sdc-" + "".join(random.choice("0123456789abcdef") for _ in range(4))
lines = [
    f"SDC_A_IP=172.30.0.{a}", f"SDC_A_HOST={tok()}",
    f"SDC_B_IP=172.30.0.{b}", f"SDC_B_HOST={tok()}",
    f"SDC_C_IP=172.30.0.{c}", f"SDC_C_HOST={tok()}",
    f"SDC_D_IP=172.30.0.{d}", f"SDC_D_HOST={tok()}",
]
open(env_path, "w").write("\n".join(lines) + "\n")
PY

# -- Build + start ------------------------------------------------------------
echo "  Building images and starting the range..."
"${COMPOSE[@]}" up -d --build 2>&1 | sed 's/^/    /'

echo ""
echo "  Waiting for the recon node (sdc-ops)..."
for i in $(seq 1 60); do
    if docker exec sdc-ops systemctl is-system-running >/dev/null 2>&1 \
        || docker exec sdc-ops test -S /run/sshd.pid 2>/dev/null \
        || docker exec sdc-ops true 2>/dev/null; then break; fi
    sleep 1
done
# Give sshd on all nodes a moment to bind.
sleep 3

# -- Place the cadet key inside sdc-ops with correct perms --------------------
docker exec sdc-ops mkdir -p /home/cadet/.ssh
docker cp "$SSH_DIR/cadet_key" sdc-ops:/home/cadet/.ssh/cadet_key
docker exec sdc-ops chown -R cadet:cadet /home/cadet/.ssh
docker exec sdc-ops chmod 600 /home/cadet/.ssh/cadet_key

# -- Arm the range: listeners + per-host nonce facts + baseline ----------------
echo ""
echo "  Arming the range (service listeners + per-host nonce attestation)..."
mkdir -p "$LAB_DIR"
ATTEST_TSV="$(mktemp)"; : > "$ATTEST_TSV"
armed_ok=1

for node in "${NODES[@]}"; do
    rp="$(role_of "$node")"; role="${rp%%:*}"; port="${rp##*:}"
    nonce="$(openssl rand -hex 8 2>/dev/null || head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"

    # Start the role's service banner listener (systemd-managed, survives rotation).
    docker exec "$node" systemctl enable --now "sdc-listener@${port}.service" >/dev/null 2>&1 || armed_ok=0
    # Plant the nonce (surfaced as the ansible_local.sdc.nonce local fact).
    docker exec "$node" bash -c "echo '$nonce' > /etc/sdc/nonce"

    ip="$(docker inspect -f '{{.NetworkSettings.Networks.fleet_net.IPAddress}}' "$node")"
    # Verify the listener is really up.
    docker exec "$node" bash -c "ss -ltn 2>/dev/null | grep -q ':${port} '" || armed_ok=0
    printf '%s\t%s\t%s\t%s\t%s\n' "$node" "$ip" "$role" "$port" "$nonce" >> "$ATTEST_TSV"
    echo "    ${node}: ${ip}  ${role} (:${port})  nonce armed"
done

# Decoy: a live host that is NOT part of the fleet — kill SSH, serve :8080 only.
docker exec sdc-decoy systemctl disable --now ssh >/dev/null 2>&1 || true
docker exec sdc-decoy systemctl enable --now "sdc-listener@8080.service" >/dev/null 2>&1 || armed_ok=0
decoy_ip="$(docker inspect -f '{{.NetworkSettings.Networks.fleet_net.IPAddress}}' sdc-decoy)"
docker exec sdc-decoy bash -c "ss -ltn 2>/dev/null | grep -q ':8080 '" || armed_ok=0
echo "    sdc-decoy: ${decoy_ip}  (decoy, :8080, no SSH)"

if [ "$armed_ok" -ne 1 ]; then
    rm -f "$ATTEST_TSV"
    echo ""; echo "  ERROR: the range failed to arm cleanly. Run 'make reset'."; exit 1
fi

# -- Write the gitignored ground-truth baseline -------------------------------
python3 - "$ATTEST_TSV" "$decoy_ip" "$LAB_DIR/baseline.json" <<'PY'
import json, sys
tsv, decoy_ip, out = sys.argv[1], sys.argv[2], sys.argv[3]
managed = []
with open(tsv) as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        node, ip, role, port, nonce = line.split("\t")
        managed.append({"token": node, "ip": ip, "role": role,
                        "port": int(port), "nonce": nonce})
baseline = {"schema": 1, "rotation_seq": 0, "subnet": "172.30.0.0/24",
            "ops_ip": "172.30.0.10", "managed": managed,
            "decoy": {"ip": decoy_ip, "port": 8080, "ssh": False}}
with open(out, "w") as f:
    json.dump(baseline, f, indent=2)
PY
rm -f "$ATTEST_TSV"
echo "    Baseline recorded: .lab/baseline.json"

echo ""
echo "=============================================="
echo "  Range ONLINE. You have ONE fact: the subnet."
echo ""
echo "    Authorized training subnet:  172.30.0.0/24"
echo ""
echo "  Board your recon node:  make shell   (then use nmap + ansible)"
echo "  Your workspace:         workspace/"
echo "  Start here:             docs/BRIEFING.md"
echo "  Verify your work:       make test"
echo "=============================================="
echo ""
