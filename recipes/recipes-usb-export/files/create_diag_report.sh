#!/bin/bash

# This script generate an archive of the current system state in order to provide data for troubleshooting
# It includes:
# - logs (dmesg, journalctl, cloud_message, fcc, be, fe)
# - appfs content (including update and supervisor logs)
# - system information (uptime, CPU load, processes, NAND usage, mnt/fcc/set content)
# - network information (interface, iptables)
# - version (RL78, FW, OS, Bootloader)
# - application status (lsscd, lsver, lsps)
# - u-boot environment
# - IO module settings stored in /tmp
#
# The generated archived is named: ${REPORT_DATE}_${FID}_diagreport.tar.gz
#
# The archive destination can be passed as argument (default is /var/log/www)

FID=$(hostname)
REPORT_NAME=$(date +%Y%m%d_%H%M%S_${FID}_diagreport.tar.gz)
REPORT_CONTENT_LOCATION=$(mktemp -d /tmp/report.XXXXXXXXXX)
REPORT_DESTINATION=${1:-/var/log/www}

echo "Generate an archive that contains system information for troubleshooting"
echo "Archive name: ${REPORT_NAME}"

echo "Export logs"
LOGS=${REPORT_CONTENT_LOCATION}/logs
mkdir -p ${LOGS}
journalctl --utc &> ${LOGS}/journalctl
dmesg &> ${LOGS}/dmesg
cp -a /var/log/{AMQP*,fcc.log*,frontend.log*,backend.log*} ${LOGS}/
cp -r /var/log/watchdog ${LOGS}/
# Don't copy previous diagreports
shopt -s extglob
cp -a /var/log/www/!(*_diagreport*) ${LOGS}/
shopt -u extglob

echo "Export system informations"
SYSTEM=${REPORT_CONTENT_LOCATION}/system
mkdir -p ${SYSTEM}
uptime &> ${SYSTEM}/uptime
ps aux &> ${SYSTEM}/ps_aux
top -n 1 -b -o %MEM &> ${SYSTEM}/top_mem
top -n 1 -b -o %CPU &> ${SYSTEM}/top_cpu
df -h &> ${SYSTEM}/df
cp -a /var/log/swupdate-fail.log* ${SYSTEM}/
cp -a /media/persistent/fcc/swupdate.log* ${SYSTEM}/
cp -a /media/persistent/system/swupdate-helpers_logs* ${SYSTEM}/
cp -a /media/persistent/system/sensor-swupdate-helpers_logs* ${SYSTEM}/
cp -a /media/persistent/system/update_supervisor.log* ${SYSTEM}/
cp -a /media/persistent/fcc/RL78_update_supervisor.log* ${SYSTEM}/
cp -a /media/persistent/fcc/ctrl_update.log* ${SYSTEM}/

echo "Export network logs and settings"
NETWORK=${REPORT_CONTENT_LOCATION}/network
mkdir -p ${NETWORK}
ifconfig &> ${NETWORK}/ifconfig
iptables-save &> ${NETWORK}/iptables-save
systemctl status systemd-resolved.service &> "${NETWORK}/status_systemd-resolved.service"
resolvectl &> "${NETWORK}/resolvectl"
# cp's "-L" (dereference: follow symbolic links) flag used here to ensure that
# the file and its content is copied instead of the symbolic link, which would
# end up being broken.
cp -aL /etc/resolv.conf "${NETWORK}/"
cp -a /media/persistent/system/config_modem ${NETWORK}/
cp -a /media/persistent/system/config_modem_logs* ${NETWORK}/
cp -a /media/persistent/system/cellular_data_supervisor_stats.csv* ${NETWORK}/

cp -a /media/persistent/system/config_wifi_logs* ${NETWORK}/
cp -a /media/persistent/system/wifi_stats.csv* ${NETWORK}/
cp -a /media/persistent/system/wifi_rssi_monitor_logs* ${NETWORK}/

cp -a /media/persistent/system/sharenet ${NETWORK}/
cp -a /media/persistent/system/wired_network ${NETWORK}/
cp -a /etc/systemd/network ${NETWORK}/


echo "Export versions"
VERSION=${REPORT_CONTENT_LOCATION}/version
mkdir -p ${VERSION}
/usr/local/bin/VersionFileBuilder
cp -a /tmp/FwVersions.txt ${VERSION}/

echo "Export application status"
MNT_FCC_SET=${REPORT_CONTENT_LOCATION}/mnt_fcc_set
mkdir -p ${MNT_FCC_SET}
cp -r /mnt/fcc/set/* ${MNT_FCC_SET}
lsscd &> ${REPORT_CONTENT_LOCATION}/lsscd
lsver &> ${REPORT_CONTENT_LOCATION}/lsver
lsps &> ${REPORT_CONTENT_LOCATION}/lsps
lsmq &> ${REPORT_CONTENT_LOCATION}/lsmq
TestClientII -d &> ${REPORT_CONTENT_LOCATION}/TestClientII
systemctl status nebula &> ${REPORT_CONTENT_LOCATION}/nebula_status
cp -a /media/persistent/fcc/log ${REPORT_CONTENT_LOCATION}/fcc_logs
cp /mnt/fcc/set/ControllerSerial.txt ${REPORT_CONTENT_LOCATION}

echo "Export u-boot environment"
UBOOT=${REPORT_CONTENT_LOCATION}/u-boot
mkdir -p ${UBOOT}
fw_printenv &> ${UBOOT}/fw_printenv

echo "Export IO module settings"
TMP=${REPORT_CONTENT_LOCATION}/tmp
mkdir -p ${TMP}
cp -a /tmp/{CFG_*,MMF_*} ${TMP}/

echo "Export RTC logs and settings"
RTC=${REPORT_CONTENT_LOCATION}/rtc
mkdir -p ${RTC}
cp -a /mnt/fcc/pidev/export/rtc/*.* ${RTC}/

echo "Create archive"
mkdir -p ${REPORT_DESTINATION}
tar czf ${REPORT_DESTINATION}/${REPORT_NAME} -C ${REPORT_CONTENT_LOCATION} .
ARCHIVE_CREATION_RESULT=$?

if [ ${ARCHIVE_CREATION_RESULT} -ne 0 ]; then
        echo "Report generation fails to create archive!!!"
fi

rm -rf ${REPORT_CONTENT_LOCATION}

sync
echo "Done"
exit ${ARCHIVE_CREATION_RESULT}
