#!/usr/bin/env bash
#
# Copyright (C) 2020 Hach
# Author: Dragan Cecavac <dcecavac@witekio.com>
#
# Mount the active persistent partition.
# It will be encrypted if not in crypto_LUKS format.

source /etc/persistent-core.sh

check_mounted
prepare_pp_hooks
ensure_encryption
mount_active_pp
