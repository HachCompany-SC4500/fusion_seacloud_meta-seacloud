# This function makes the target system accept every login attempt
# on root without any authentication.
allow_root_access_without_password() {
    sed -i 's/^root:[^:]*:/root::/g' "${IMAGE_ROOTFS}/${sysconfdir}/passwd"
    sed -i 's/^root:[^:]*:/root::/g' "${IMAGE_ROOTFS}/${sysconfdir}/shadow"
}

# This function disable some of the restrictions applied in the SSHD configuration
# file regarding authentication
disable_ssh_authentication_restrictions() {
    SSHD_CONFIG_FILES=" \
        ${IMAGE_ROOTFS}/${sysconfdir}/ssh/sshd_config \
        ${IMAGE_ROOTFS}/${sysconfdir}/ssh/sshd_config_readonly \
    "

    # Allow root or any user to login

    for config in ${SSHD_CONFIG_FILES}
    do
        if [ -e "${config}" ]
        then
            sed -i '/^[[:space:]]*AllowGroups/d' "${config}"
            sed -i 's/^[#[:space:]]*\(PermitRootLogin\).*/\1 yes/' "${config}"
        fi
    done
}

# The generated target system is open, i.e. root is accessible to anyone and
# SSH accepts any authentication method. A systemd (secure-controller.service)
# on the target system is in charge of closing those access when the
# controller is not in development mode.
ROOTFS_POSTPROCESS_COMMAND += "allow_root_access_without_password; "
ROOTFS_POSTPROCESS_COMMAND += "disable_ssh_authentication_restrictions; "
