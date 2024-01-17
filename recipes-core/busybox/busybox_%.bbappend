FILESEXTRAPATHS_prepend := "${THISDIR}/busybox:"

SRC_URI += "file://devmem.cfg \
            file://timeout.cfg \
"

# Do not auto-start busybox-syslog.service and thus /sbin/syslogd
SYSTEMD_SERVICE_${PN}-syslog = ""
FILES_${PN}-syslog += "/lib/systemd/system/*"
