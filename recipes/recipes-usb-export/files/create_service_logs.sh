#!/bin/bash

# service logs archive file name
REPORT_NAME=$(date +%Y%m%d_%H%M%S_$(hostname)_service_logs.zip)
# tmp folder to create the archive
TMP_LOGS_FOLDER="/tmp/service-logs"

# folder to write the archive to. If it does not begin by /, add current folder before
if [[ $1 =~ ^/ ]]; then
EXPORT_FOLDER=$1
else
EXPORT_FOLDER="$(pwd)/$1"
fi

# create folder if they don't exist
mkdir -p $TMP_LOGS_FOLDER
mkdir -p $EXPORT_FOLDER

pushd $TMP_LOGS_FOLDER > /dev/null

# device logs, if this script was called with a second parameter "--service-logger", flag the need to export the logger file
if [[ ! -z "$2" && $2 = "--service-logger" ]]; then
device_logs.py --logger-file=$TMP_LOGS_FOLDER --export-to Devices_Logs
else
device_logs.py --export-to Devices_Logs
fi
# exit as soon as possible if the export folder has vanished
[ $? != 0 ] || [ ! -d $EXPORT_FOLDER ] && exit 1

# diagnostic report
create_diag_report.sh .

# exit as soon as possible if the export folder has vanished
[ $? != 0 ] || [ ! -d $EXPORT_FOLDER ] && exit 1

# versions
VersionFileBuilder
cp /tmp/FwVersions.txt controller_details.txt
# device details
lsscd > sc_devices_details.txt
# connectivity details
get_connectivity_details.sh > connectivity_details.txt
#controller settings
cp /media/persistent/befe/controllerSettings.json controller_settings.json
# last performance auto test result
cp /media/persistent/befe/performance_auto_test_result.json .
# ethernet port mode
cp /media/persistent/system/ethernet_port_selection ethernet_port_selection.txt

# software options (ModbusTCP / Prognosys / Claros / Nebula)
# get infos
modbus=`config_sw_options.py --get 1_40963 | sed 's/1_40963 //'`
prognosys=`config_sw_options.py --get 1_40968 | sed 's/1_40968 //'`
claros=`config_claros.py status`
nebula=`config_nebula.py -g`
# build file
option_filename="software_options.txt"
echo "Software options:" > $option_filename
echo "`config_sw_options.py --status-hr | sed 's/^/\t/'`" >> $option_filename
echo >> $option_filename
echo "Claros status:" >> $option_filename
echo -e "\tClaros -> $claros" >> $option_filename
echo -e "\tNebula database targeted -> $nebula" >> $option_filename

# exit as soon as possible if the export folder has vanished
[ ! -d $EXPORT_FOLDER ] && exit 1

# get the password
PASSWORD=`/usr/local/bin/service_logs_pwd.py`
ERROR=$?

# create the archive to the destination folder, if password was properly generated
[[ $ERROR -eq 0 ]] && zip -P $PASSWORD -r $EXPORT_FOLDER/$REPORT_NAME *

sync

popd > /dev/null

# remove tmp folder
rm -rf $TMP_LOGS_FOLDER

# to return non zero value if the archive has not been created
ls $EXPORT_FOLDER/$REPORT_NAME
