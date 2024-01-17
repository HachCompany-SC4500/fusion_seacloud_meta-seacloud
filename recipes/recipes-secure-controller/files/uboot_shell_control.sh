#!/bin/sh

readonly SET_ENV="/sbin/fw_setenv"
readonly GET_ENV="/sbin/fw_printenv -n"
readonly UNLOCK_VAR="uboot_cmdline_unmask_key"

. /etc/persistent-core.sh

fetch_and_hash_key() {
    # After fetch_encryption_key() is called, the variable ${key} contains the encryption key
    # stored in the fuses.
    fetch_encryption_key

    # fetch_encryption_key() creates a temporary file ${key_file} containing the fetched key,
    # but we don't need it here so we remove it immediately.
    [ -f "${key_file}" ] && rm -f "${key_file}"

    key_hash=$(printf "%s" "${key}" | sha256sum | cut -f1 -d " ")
}

uboot_env_lock() {
    echo 1 > /sys/block/mmcblk0boot0/force_ro
}

uboot_env_unlock() {
    echo 0 > /sys/block/mmcblk0boot0/force_ro
}

unlock_uboot_cli() {
    ${SET_ENV} bootdelay 2
    fetch_and_hash_key
    ${SET_ENV} ${UNLOCK_VAR} "${key_hash}"
}

lock_uboot_cli() {
    ${SET_ENV} -- bootdelay -2
    ${SET_ENV} ${UNLOCK_VAR}
}

print_uboot_cli_status() {
    # "|| true" is appended to the command here to not stop the script
    # in case ${UNLOCK_VAR} does not exist in the bootloader environment.
    # This would mean that the bootloader shell is locked.
    from_env="$(${GET_ENV} "${UNLOCK_VAR}" 2> /dev/null || true)"

    # After this function is called, the hashed key is stored in ${key_hash}
    fetch_and_hash_key

    [ "${from_env}" = "${key_hash}" ] && status="unlocked" || status="locked"
    printf "%s\\n" "${status}"
}

CMD=${1}

case ${CMD} in
    unlock )
        echo "----------- Un-Locking Uboot Shell ------------------"
        uboot_env_unlock
        unlock_uboot_cli
        uboot_env_lock
        ;;
    lock )
        echo "------------ Locking Uboot Shell --------------------"
        uboot_env_unlock
        lock_uboot_cli
        uboot_env_lock
        ;;
    status )
        print_uboot_cli_status
        ;;
    * )
        echo "--------------Usage Info---------------------------"
        echo "Usage:: uboot_shell_control.sh lock|unlock|status"
        ;;
esac
