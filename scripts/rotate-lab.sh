#!/usr/bin/env bash
# =============================================================================
# rotate-lab.sh — Nyx, the Signal Ghost, moves the fleet.
#
# Live-rotates every managed node onto a NEW address (no container restart, so
# the 0.0.0.0 service listeners and sshd keep serving) and refreshes the per-host
# nonce. A static hosts.yml now points at dead IPs; only a discovery-based
# (dynamic) inventory re-finds the fleet. Updates .lab/baseline.json in place.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
LAB_DIR="$ROOT_DIR/.lab"
BASELINE="$LAB_DIR/baseline.json"

if [ ! -f "$BASELINE" ]; then
    echo "  No baseline found — run 'make setup' first."; exit 1
fi

echo ""
echo "  >> Nyx, the Signal Ghost, rotates the fleet's addressing..."

# Choose new, free host octets (avoid .1, .10 ops, current decoy, and each other).
mapfile -t NEW_OCTETS < <(python3 - "$BASELINE" <<'PY'
import json, random, sys
b = json.load(open(sys.argv[1]))
used = {1, 10}
used.add(int(b["decoy"]["ip"].split(".")[-1]))
for m in b["managed"]:
    used.add(int(m["ip"].split(".")[-1]))
pool = [o for o in range(20, 241) if o not in used]
random.shuffle(pool)
print("\n".join(str(o) for o in pool[:len(b["managed"])]))
PY
)

# Rotate each managed node and refresh its nonce.
i=0
declare -a NEWMAP=()
NODE_LIST=$(python3 -c 'import json,sys; b=json.load(open(sys.argv[1])); print(" ".join(m["token"] for m in b["managed"]))' "$BASELINE")
for node in $NODE_LIST; do
    newip="172.30.0.${NEW_OCTETS[$i]}"
    nonce="$(openssl rand -hex 8 2>/dev/null || head -c 8 /dev/urandom | od -An -tx1 | tr -d ' \n')"
    docker network disconnect fleet_net "$node"
    docker network connect --ip "$newip" fleet_net "$node"
    docker exec "$node" bash -c "echo '$nonce' > /etc/sdc/nonce"
    NEWMAP+=("${node}=${newip}=${nonce}")
    echo "    ${node} -> ${newip}"
    i=$((i+1))
done

# Give the reattached interfaces a moment to settle.
sleep 2

# Update the baseline in place (new IPs + nonces, bump rotation_seq).
python3 - "$BASELINE" "${NEWMAP[@]}" <<'PY'
import json, sys
baseline_path = sys.argv[1]
updates = {}
for kv in sys.argv[2:]:
    node, ip, nonce = kv.split("=")
    updates[node] = (ip, nonce)
b = json.load(open(baseline_path))
for m in b["managed"]:
    if m["token"] in updates:
        m["ip"], m["nonce"] = updates[m["token"]]
b["rotation_seq"] = b.get("rotation_seq", 0) + 1
json.dump(b, open(baseline_path, "w"), indent=2)
PY

echo "    Baseline updated (rotation_seq bumped). The static map is now stale."
echo ""
