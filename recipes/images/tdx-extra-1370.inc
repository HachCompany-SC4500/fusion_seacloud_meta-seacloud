#additional packages to include in our Toradex images

# Copy Licenses to image /usr/share/common-licenses, on vybrid for flash size reasons only the manifest
COPY_LIC_MANIFEST ?= "1"
#Bug with several MACHINES build, license files for all arch packages stored wrongly
COPY_LIC_DIRS ?= "1"

add_rootfs_version () {
    echo -n "${IMAGE_NAME} ${PV}" >> ${IMAGE_ROOTFS}/etc/issue
    echo " ${TDX_VERDATE}" | sed 's/-//' >>${IMAGE_ROOTFS}/etc/issue
    echo "" >> ${IMAGE_ROOTFS}/etc/issue
}

PV = "${TDX_VER_PACKAGE_MIN}"

# add the rootfs version to the welcome banner
ROOTFS_POSTPROCESS_COMMAND += " add_rootfs_version;"

IMAGE_INSTALL_append_mx7 = " \
    aspell \
    file \
    libusbgx \
    libusbgx-examples \
    linuxptp \
    ptpd \
    u-boot-fw-utils \
"
IMAGE_INSTALL_append_colibri-imx7-emmc = " \
    perf \
"
IMAGE_INSTALL_append_colibri-imx7 = " \
    mtd-utils-ubifs \
"

IMAGE_INSTALL += " \
    sqlite3 \
    \
    ${WIFI} \
    curl \
    iproute2 \
    \
    gdbserver \
    bzip2 \
    grep \
    minicom \
    ldd \
    lsof \
    mtd-utils \
    dosfstools \
    util-linux \
    util-linux-fstrim \
    \
    devmem2 \
    ethtool \
    evtest \
    hdparm \
    i2c-tools \
    libsoc \
    mmc-utils-cos \
    util-linux-lsblk \
    \
    tdx-oak-sensors \
"

# Wi-Fi FW and Packages

WIFI = " \
    hostapd \
    linux-firmware-ath10k    \
    linux-firmware-sd8686    \
    linux-firmware-sd8688    \
    linux-firmware-sd8787    \
    linux-firmware-sd8797    \
    linux-firmware-sd8887    \
    linux-firmware-sd8997    \
    linux-firmware-ralink    \
    linux-firmware-rtl8192cu \
    linux-firmware-rtl8188eu \
    wireless-regdb-static \
"
WIFI_EXTRA = " \
    linux-firmware-ath9k     \
    linux-firmware-iwlwifi   \
"

IMAGE_INSTALL_append_apalis-tk1 = " \
    backports \
    ${WIFI_EXTRA} \
"

IMAGE_INSTALL_append_apalis-tk1-mainline = " \
    ${WIFI_EXTRA} \
"

IMAGE_INSTALL_append_apalis-imx6 = " \
    ${WIFI_EXTRA} \
"

IMAGE_INSTALL_append_mx8 = " \
    bluez-alsa \
    mwifiexap \
    ${WIFI_EXTRA} \
"

