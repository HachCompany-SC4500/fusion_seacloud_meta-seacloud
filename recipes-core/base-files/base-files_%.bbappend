FILESEXTRAPATHS_prepend := "${THISDIR}/files:"

SRC_URI += " \
    file://hostname \
    file://bash_aliases.sh \
    file://eagle_aliases.sh \
"

do_configure_prepend() {
    # Content of /media is located in the RAM. This allow to mount
    # devices' filesystem even when the root filesystem is running out of space.
    # This makes the content of /media volatile. This is acceptable as it is
    # only used to contain mount-points for other filesystems; those don't
    # become volatile.
    sed -i -e '$a tmpfs /media tmpfs defaults 0 0' ${WORKDIR}/fstab
}

do_install_append() {
    install -d ${D}/${sysconfdir}
    install -m 0644 ${WORKDIR}/hostname ${D}/${sysconfdir}/hostname

    install -d ${D}/${sysconfdir}/profile.d
    install -m 0644 ${WORKDIR}/bash_aliases.sh ${D}/${sysconfdir}/profile.d
    install -m 0644 ${WORKDIR}/eagle_aliases.sh ${D}/${sysconfdir}/profile.d
}

FILES_${PN} += " \
    ${sysconfdir}/hostname \
    ${sysconfdir}/profile.d/bash_aliases.sh \
    ${sysconfdir}/profile.d/eagle_aliases.sh \
"
