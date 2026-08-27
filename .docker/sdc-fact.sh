#!/bin/sh
# Ansible local fact: exposes this node's range nonce as ansible_local.sdc.nonce.
# The nonce is planted by setup-lab.sh / rotate-lab.sh in /etc/sdc/nonce, so it
# can only be read via a live facts sweep — never from the repo.
printf '{"nonce":"%s"}\n' "$(cat /etc/sdc/nonce 2>/dev/null)"
