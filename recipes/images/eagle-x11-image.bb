SUMMARY = "Hach Eagle BSP"
DESCRIPTION = "Eagle BSP based on Freescale, Toradex and Custom Hach Sources"

LICENSE = "MIT"

inherit core-image

#start of the resulting deployable tarball name
export IMAGE_BASENAME = "X11-Image"

IMAGE_NAME_colibri-imx7-emmc-1370 = "Colibri-iMX7-eMMC-Eagle_${IMAGE_BASENAME}"
IMAGE_NAME = "${MACHINE}_${IMAGE_BASENAME}"

require tdx-image-fstype.inc

# This file disables elementary security features in the produced image (e.g. it
# makes root access open for everyone).
# During an SWUpdate process, if the updated controller is not in development
# mode, those accesses will be closed through the update process.
# Systems installed through the Tezi process (never done on deployed controllers)
# keep those full system accesses open until the development mode is manually disabled.
require eagle-disable-security.inc

# This file includes extra's which we were not able to get into
# other yocto means , currently it includes postprocessing for
# creating symbolic links for zlib recipe libz.so->libz.so.1
include eagle-x11-image-extra.inc

SYSTEMD_DEFAULT_TARGET = "graphical.target"

IMAGE_FEATURES += " \
    ${@bb.utils.contains('DISTRO_FEATURES', 'wayland', '', \
       bb.utils.contains('DISTRO_FEATURES',     'x11', 'x11', \
                                                       '', d), d)} \
"

IMAGE_LINGUAS = "en-us"
#IMAGE_LINGUAS = "de-de fr-fr en-gb en-us pt-br es-es kn-in ml-in ta-in"
#ROOTFS_POSTPROCESS_COMMAND += 'install_linguas; '

ROOTFS_PKGMANAGE_PKGS ?= '${@oe.utils.conditional("ONLINE_PACKAGE_MANAGEMENT", "none", "", "${ROOTFS_PKGMANAGE}", d)}'

CONMANPKGS ?= "connman connman-plugin-loopback connman-plugin-ethernet connman-plugin-wifi connman-client"

IMAGE_INSTALL += " \
    packagegroup-boot \
    udev-extra-rules \
    ${CONMANPKGS} \
    ${ROOTFS_PKGMANAGE_PKGS} \
    timestamp-service \
    ${@bb.utils.contains('DISTRO_FEATURES', 'wayland', \
                         'weston weston-init wayland-terminal-launch', '', d)} \
    ${@bb.utils.contains('DISTRO_FEATURES', 'x11 wayland', \
                         'weston-xwayland xterm', '', d)} \
"

IMAGE_INSTALL_append_mx7 = " \
    gpio-tool \
    mime-support \
"

IMAGE_INSTALL_append_colibri-imx7-emmc-1370 = " \
    u-boot-toradex-fw-utils \
    perf \
"

IMAGE_INSTALL += " \
    procps \
    eject \
    xdg-utils \
    \
    libgsf \
    libxres \
    makedevs \
    xcursor-transparent-theme \
    zeroconf \
    timestamp-service \
    packagegroup-base-extended \
    ${XSERVER} \
    xserver-common \
    xauth \
    xhost \
    xset \
    setxkbmap \
    \
    xrdb \
    xorg-minimal-fonts \
    xserver-xorg-utils \
    \
    libxdamage \
    libxvmc \
    libxinerama \
    libxcursor \
    \
    bash \
    \
    libpcre \
    libpcreposix \
    libxcomposite \
    \
    x11vnc \
    sudo \
    \
    avahi-daemon \
    avahi-utils \
    alsa-utils-alsamixer \
    usbutils \
    iw \
    wpa-supplicant \
    tzdata \
    tzdata-africa \
    tzdata-americas \
    tzdata-antarctica \
    tzdata-arctic \
    tzdata-asia \
    tzdata-atlantic \
    tzdata-australia \
    tzdata-europe \
    tzdata-misc \
    tzdata-pacific \
    cpufrequtils \
    htop \
    openssh \
    python3 \
    python3-dbus \
    python3-pyserial \
    python3-netifaces \
    python3-fcntl \
    python3-misc \
    python3-six \
    python3-pyudev \
    python3-socketio \
    systemd-analyze \
    \
    ntfs-3g \
    fuse-exfat \
    \
    cukinia-tests \
"

# Eagle project specifics
IMAGE_INSTALL += " \
    diagnose \
    eagle-controller-befe \
    secure-controller \
    fcc-eagle \
    usb-export \
    garbage-collector \
    \
    rng-tools \
    \
    python-ctypes \
    python-subprocess \
    python-pyudev \
    python-enum34 \
    python-shell \
    python-pyserial \
    python-json \
    python-ipaddress \
    python-multiprocessing \
    python3-pygobject \
    \
    cryptsetup \
    cryptodev-module \
    persistent-crypto \
    persistent-storage \
    \
    connection-sharing \
    ofono \
    ofono-tests \
    openvpn \
    wifi \
    cellular \
    boost \
    \
    imagemagick \
    libavahi-compat-libdnssd \
    custom-python-apps \
    custom-python2-libs \
    custom-python3-libs \
    rl78-firmware \
    \
    tslib tslib-conf tslib-calibrate tslib-uinput tslib-tests \
    xinput \
    \
    utouch-evemu \
    uinput-calibration \
    source-han-sans-kr-fonts \
    packagegroup-fonts-truetype-chinese \
    packagegroup-fonts-truetype-japanese \
    zip \
    watchdog-keepalive \
    configure-coredumps \
"

PACKAGE_EXCLUDE_pn-eagle-x11-image = "dropbear"
PACKAGE_EXCLUDE_pn-eagle-x11-image = "packagegroup-core-ssh-dropbear"

# To have the wt static dev package into the SDK
TOOLCHAIN_TARGET_TASK_append = " wt-staticdev uamqp-staticdev"

require tdx-extra-1370.inc

IMAGE_DEV_MANAGER   = "udev"
IMAGE_INIT_MANAGER  = "systemd"
IMAGE_INITSCRIPTS   = " "
IMAGE_LOGIN_MANAGER = "busybox shadow"

# While solving a issue with ownership when building with Bamboo (FCON2-1382),
# we noticed that some files on the target system had invalid ownership.
# Ownership information from the building agent leaked in the generated image.
# This is the case for the license files.
fix_license_files_ownership() {
    chown -R root:root "${IMAGE_ROOTFS}/usr/share/common-licenses/"
}

ROOTFS_POSTPROCESS_COMMAND += "fix_license_files_ownership; "

# Image level user configuration
inherit extrausers
EXTRA_USERS_PARAMS = "\
    usermod -a -G _befe _backend; \
    usermod -a -G _befe _frontend; \
    usermod -a -G _fcc_extra_group _fcc; \
"
