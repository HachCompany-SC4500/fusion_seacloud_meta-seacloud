SUMMARY = "Hach Eagle BSP"
DESCRIPTION = "Eagle BSP based on Freescale, Toradex and Custom Hach Sources"

LICENSE = "MIT"

#start of the resulting deployable tarball name
export IMAGE_BASENAME = "LXDE-Image"
IMAGE_NAME_apalis-imx6 = "Apalis-iMX6_${IMAGE_BASENAME}"
IMAGE_NAME_apalis-t30 = "Apalis-T30_${IMAGE_BASENAME}"
IMAGE_NAME_apalis-tk1 = "Apalis-TK1_${IMAGE_BASENAME}"
IMAGE_NAME_apalis-tk1-mainline = "Apalis-TK1-Mainline_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-imx6 = "Colibri-iMX6_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-imx6ull = "Colibri-iMX6ULL_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-imx7 = "Colibri-iMX7_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-imx7-emmc = "Colibri-iMX7-eMMC_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-imx7-emmc-1370 = "Colibri-iMX7-eMMC-Eagle_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-pxa = "Colibri-PXA_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-t20 = "Colibri-T20_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-t30 = "Colibri-T30_${IMAGE_BASENAME}"
IMAGE_NAME_colibri-vf = "Colibri-VF_${IMAGE_BASENAME}"
IMAGE_NAME = "${MACHINE}_${IMAGE_BASENAME}"

SYSTEMD_DEFAULT_TARGET = "graphical.target"

#create the deployment directory-tree
# require recipes-images/images/tdx-image-fstype.inc
require tdx-image-fstype.inc

IMAGE_LINGUAS = "en-us"
#IMAGE_LINGUAS = "de-de fr-fr en-gb en-us pt-br es-es kn-in ml-in ta-in"
#ROOTFS_POSTPROCESS_COMMAND += 'install_linguas; '

DISTRO_UPDATE_ALTERNATIVES ??= ""
ROOTFS_PKGMANAGE_PKGS ?= '${@oe.utils.conditional("ONLINE_PACKAGE_MANAGEMENT", "none", "", "${ROOTFS_PKGMANAGE} ${DISTRO_UPDATE_ALTERNATIVES}", d)}'

CONMANPKGS ?= "connman connman-client connman-gnome"

#deploy the OpenGL ES headers to the sysroot
DEPENDS_append_tegra = " nvsamples"

IMAGE_BROWSER = "firefox"
#keep the rootfs size small
IMAGE_BROWSER_colibri-imx6ull = ""
IMAGE_BROWSER_colibri-vf = ""

# don't install some packages bloating the vybrid image
BAD_RECOMMENDATIONS_append_colibri-vf = " udev-hwdb cpufrequtils"

# this would pull in a large amount of gst-plugins, we only add a selected few
#    gstreamer1.0-plugins-base-meta
#    gstreamer1.0-plugins-good-meta
#    gstreamer1.0-plugins-bad-meta
#    gst-ffmpeg
#GSTREAMER = " \
#    gstreamer1.0 \
#    gstreamer1.0-plugins-base \
#    gstreamer1.0-plugins-base-typefindfunctions \
#    gstreamer1.0-plugins-base-ogg \
#    gstreamer1.0-plugins-base-theora \
#    gstreamer1.0-plugins-base-videotestsrc \
#    gstreamer1.0-plugins-base-vorbis \
#    gstreamer1.0-plugins-good-audioparsers \
#    gstreamer1.0-plugins-good-autodetect \
#    gstreamer1.0-plugins-good-avi \
#    gstreamer1.0-plugins-good-deinterlace \
#    gstreamer1.0-plugins-good-id3demux \
#    gstreamer1.0-plugins-good-isomp4 \
#    gstreamer1.0-plugins-good-matroska \
#    gstreamer1.0-plugins-good-multifile \
#    gstreamer1.0-plugins-good-rtp \
#    gstreamer1.0-plugins-good-rtpmanager \
#    gstreamer1.0-plugins-good-udp \
#    gstreamer1.0-plugins-good-video4linux2 \
#    gstreamer1.0-plugins-good-wavenc \
#    gstreamer1.0-plugins-good-wavparse \
#"
# No longer available
#    gst-plugins-base-decodebin \
#    gst-plugins-base-decodebin2 \
#    gst-plugins-base-playbin \
#    gst-plugins-ugly-asf \
#    gstreamer1.0-plugins-base-alsa \
#    gstreamer1.0-plugins-base-audioconvert \
#    gstreamer1.0-plugins-base-audioresample \
#    gstreamer1.0-plugins-base-audiotestsrc \
#"

GSTREAMER_MX6QDL = " \
    gstreamer1.0-plugins-base-ximagesink \
    gstreamer1.0-plugins-imx \
    imx-gst1.0-plugin \
    imx-gst1.0-plugin-gplay \
    imx-gst1.0-plugin-grecorder \
"
GSTREAMER_append_mx6q = "${GSTREAMER_MX6QDL}"
GSTREAMER_append_mx6dl = "${GSTREAMER_MX6QDL}"

GSTREAMER_colibri-imx6ull = ""

#GSTREAMER_append_mx7 = " \
#    gstreamer1.0-plugins-base-ximagesink \
#    imx-gst1.0-plugin \
#"
# No longer available
#    gst-plugins-gl \
#    gst-fsl-plugin \
#

# use gstreamer-0.10 for tegra
GSTREAMER_tegra = " \
    gstreamer \
    gst-plugins-base \
    gst-plugins-base-alsa \
    gst-plugins-base-audioconvert \
    gst-plugins-base-audioresample \
    gst-plugins-base-audiotestsrc \
    gst-plugins-base-decodebin \
    gst-plugins-base-decodebin2 \
    gst-plugins-base-playbin \
    gst-plugins-base-typefindfunctions \
    gst-plugins-base-ivorbisdec \
    gst-plugins-base-ogg \
    gst-plugins-base-theora \
    gst-plugins-base-videotestsrc \
    gst-plugins-base-vorbis \
    gst-plugins-good-audioparsers \
    gst-plugins-good-autodetect \
    gst-plugins-good-avi \
    gst-plugins-good-deinterlace \
    gst-plugins-good-id3demux \
    gst-plugins-good-isomp4 \
    gst-plugins-good-matroska \
    gst-plugins-good-rtp \
    gst-plugins-good-rtpmanager \
    gst-plugins-good-udp \
    gst-plugins-good-video4linux2 \
    gst-plugins-good-wavenc \
    gst-plugins-good-wavparse \
    gst-plugins-ugly-asf \
"
GSTREAMER_append_tegra3 = " \
    gst-plugins-good-jpeg \
"
GSTREAMER_append_tegra124 = " \
    gstreamer1.0-libav \
    gstreamer1.0-plugins-bad-videoparsersbad \
    gstreamer \
    gst-plugins-base \
    gst-plugins-base-alsa \
    gst-plugins-base-audioconvert \
    gst-plugins-base-audioresample \
    gst-plugins-base-audiotestsrc \
    gst-plugins-base-decodebin \
    gst-plugins-base-decodebin2 \
    gst-plugins-base-playbin \
    gst-plugins-base-typefindfunctions \
    gst-plugins-base-ogg \
    gst-plugins-base-theora \
    gst-plugins-base-videotestsrc \
    gst-plugins-base-vorbis \
    gst-plugins-base-ximagesink \
    gst-plugins-base-xvimagesink \
    gst-plugins-good \
    gst-plugins-good-audioparsers \
    gst-plugins-good-autodetect \
    gst-plugins-good-avi \
    gst-plugins-good-deinterlace \
    gst-plugins-good-id3demux \
    gst-plugins-good-isomp4 \
    gst-plugins-good-matroska \
    gst-plugins-good-rtp \
    gst-plugins-good-rtpmanager \
    gst-plugins-good-udp \
    gst-plugins-good-video4linux2 \
    gst-plugins-good-wavenc \
    gst-plugins-good-wavparse \
    libgstcodecparsers-1.0 \
    libgstnvegl \
    libgstomx-0.10 \
    libgstomx-1.0 \
"
GSTREAMER_colibri-vf = ""

# No gstreamer support
GSTREAMER_colibri-imx7-emmc = ""
GSTREAMER_colibri-imx7-emmc-1370 = ""

IMAGE_INSTALL_append_tegra = " \
    gpio-tool \
    tegrastats-gtk \
    gnome-disk-utility \
    mime-support \
    eglinfo-x11 \
    xvinfo \
"
IMAGE_INSTALL_append_tegra3 = " \
    \
"
IMAGE_INSTALL_append_tegra124 = " \
    gpio-tool \
    gnome-disk-utility \
    libglu \
    mesa-demos \
    freeglut \
    mime-support \
    tiff \
    xvinfo \
    \
"
IMAGE_INSTALL_append_tegra124m = " \
    gpio-tool \
    gnome-disk-utility \
    libglu \
    mesa-demos \
    freeglut \
    mime-support \
    tiff \
    xvinfo \
    \
"
IMAGE_INSTALL_MX6QDL = " \
    gpio-tool \
    packagegroup-fsl-gpu-libs \
    libopencl-imx \
    gnome-disk-utility \
    mime-support \
    eglinfo-x11 \
    \
"
IMAGE_INSTALL_append_mx6q = "${IMAGE_INSTALL_MX6QDL}"
IMAGE_INSTALL_append_mx6dl = "${IMAGE_INSTALL_MX6QDL}"

IMAGE_INSTALL_append_mx7 = " \
    gpio-tool \
    mime-support \
"
IMAGE_INSTALL_append_vf = " \
    gpio-tool \
    xf86-video-modesetting \
"

IMAGE_INSTALL_append_colibri-imx6ull = " \
    gpio-tool \
"

# Packages which might be empty or no longer available
RRECOMMENDS_${PN} += " \
    xserver-xorg-multimedia-modules \
    xserver-xorg-extension-dbe \
    xserver-xorg-extension-extmod \
"

IMAGE_INSTALL += " \
    eject \
    gconf \
    gvfs \
    gvfsd-trash \
    xdg-utils \
    \
    libgsf \
    libxres \
    makedevs \
    xcursor-transparent-theme \
    zeroconf \
    packagegroup-basic \
    udev-extra-rules \
    ${CONMANPKGS} \
    ${ROOTFS_PKGMANAGE_PKGS} \
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
    xserver-xorg-utils \
    \
    libxdamage libxvmc libxinerama \
    libxcursor \
    \
    bash \
    \
    ${GSTREAMER} \
    v4l-utils \
    libpcre \
    libpcreposix \
    libxcomposite \
    \
    x11vnc \
    python3 \
    python3-dbus \
    python3-pyserial \
    python3-netifaces \
"

# Eagle project specifics
IMAGE_INSTALL += " \
    1370testtool \
    diagnose \
    cups \
    eagle-controller-backend \
    eagle-controller-frontend \
    \
    libxscrnsaver \
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
    \
    ofono \
    openvpn \
    boost \
    sudo \
    imagemagick \
    libavahi-compat-libdnssd \
    custom-python-apps \
    custom-python2-libs \
    custom-python3-libs \
"
# wt

require tdx-extra-1370.inc

# start of tdx-extra.inc customization

IMAGE_INSTALL_append_colibri-imx7-emmc = " \
    u-boot-toradex-fw-utils \
    perf \
"

IMAGE_INSTALL_append_colibri-imx7-emmc-1370 = " \
    u-boot-toradex-fw-utils \
    perf \
"

# end of tdx-extra.inc customization

# start of lx.inc customization

# No need to calibrate capacitive touchscreen
IMAGE_INSTALL_remove_colibri-imx7-emmc = "xinput-calibrator"
IMAGE_INSTALL_remove_colibri-imx7-emmc = "lxdm"
IMAGE_INSTALL_remove_colibri-imx7-emmc-1370 = "xinput-calibrator"
IMAGE_INSTALL_remove_colibri-imx7-emmc-1370 = "lxdm"

# end of lx.inc customization

# To have the wt static dev package into the SDK
TOOLCHAIN_TARGET_TASK_append = " wt-staticdev uamqp-staticdev"

IMAGE_DEV_MANAGER   = "udev"
IMAGE_INIT_MANAGER  = "systemd"
IMAGE_INITSCRIPTS   = " "
IMAGE_LOGIN_MANAGER = "busybox shadow"

IMAGE_INSTALL_remove = "backports"

inherit core-image
