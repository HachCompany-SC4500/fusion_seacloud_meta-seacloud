HOMEPAGE = "http://www.ofono.org"
SUMMARY  = "open source telephony"
DESCRIPTION = "oFono is a stack for mobile telephony devices on Linux. oFono supports speaking to telephony devices through specific drivers, or with generic AT commands."
LICENSE  = "GPLv2"
LIC_FILES_CHKSUM = "file://COPYING;md5=eb723b61539feef013de476e68b5c50a"

inherit autotools pkgconfig update-rc.d systemd bluetooth

DEPENDS  = "dbus glib-2.0 udev mobile-broadband-provider-info"

INITSCRIPT_NAME = "ofono"
INITSCRIPT_PARAMS = "defaults 22"
 
PACKAGECONFIG ??= "\
    ${@bb.utils.contains('DISTRO_FEATURES', 'systemd', 'systemd', '', d)} \
    ${@bb.utils.contains('DISTRO_FEATURES', 'bluetooth', 'bluez', '', d)} \
    "

PACKAGECONFIG[systemd] = "--with-systemdunitdir=${systemd_unitdir}/system/,--with-systemdunitdir="
PACKAGECONFIG[bluez] = "--enable-bluetooth, --disable-bluetooth, ${BLUEZ}"

EXTRA_OECONF += "--enable-test"

# no bluetooth for the moment. It sends annoying message so disable it
EXTRA_OECONF += "--disable-bluetooth"

#Just to avoid the service starts after installation
SYSTEMD_AUTO_ENABLE ??= "disable"

SYSTEMD_SERVICE_${PN} = "ofono.service"

PACKAGES =+ "${PN}-tests"

RDEPENDS_${PN} += "dbus"

FILES_${PN} += "${base_libdir}/udev ${systemd_unitdir}"

FILES_${PN}-tests = "${libdir}/${BPN}/test"
RDEPENDS_${PN}-tests = "python python-pygobject python-dbus"
