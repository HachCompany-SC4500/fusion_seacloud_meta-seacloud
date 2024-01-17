#!/usr/bin/python3

from enum import Enum
import logging
import lib_logger
import re
import subprocess
import sys
import os
import getopt
import lib_system

class Log_type(Enum):
        DATA = 1
        EVENT = 2

# Base path where Plugin-devices export their data
pidev_export_path_base = '/mnt/fcc/pidev/export/'

# Data needed for logger file export
service_logger_export_path_base = ''
logger_file_requested = False
logger_file_number_list = {"NT3100sc":24, "NT3200sc":24}

def print_usage():
    print("device_logs.py usage:")
    print("-h / --help : to display this help")
    print("--logger-file : flag and folder where to export the service logger file if available, currently for NT3x device")
    print("--export-to : export all devices logs to destination directory specified as second argument")
    print("--get-pidev-export-path : print base path where Plugin-devices export their data (used by backend)")

# Return if the given device name has a specific logger file
def device_has_logger_file(device_name):
        if device_name in logger_file_number_list:
                return True
        return False

# Copy the data and event logs to a given location
def export_to(folder_path_base):

        # create the output folder if necessary
        if not os.path.exists(folder_path_base):
            os.makedirs(folder_path_base)

        # get the slots connected
        lsscd_response = subprocess.check_output("lsscd", shell=True)

        lsscd_response = lsscd_response.decode("utf-8").replace("\r", "")
        # get all the device info, except Prognosys (19) and ModbusTCP (18)
        # e.g : [('0', 'LDO2', '121530000074'), ('4', '4-20mA', '2009C1207274'), ('5', 'INT HV RELAY', '000000002066'),  ('20', 'RTC-P', '000009999119')]
        device_infos = re.findall('Slot (?!18\n)(?!19\n)(\d+)\ndev_name[ ]*= (.*)\nfusion_id[ ]*= HL[0-9]{3}_[0-9]{5}_(.*)\nmodbus_adr[ ]*= .*\nlocation[ ]*= ".*"\n', lsscd_response)

        ###############
        # This bool is used to generate fake file on USB
        # We will remove it when CSV generation will be stable
        ###############
        fake = False

        # Manage particular case of plugin devices (pidev) where we want to export pidev settings to destination folder
        pidev_settings_exported = False

        ##########
        # get system date
        try:
                timedatectl_output = str(subprocess.check_output('timedatectl', shell=True).decode("utf-8"))

                regex_timedate='Local time:.*([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2}):([0-9]{2})'
                match = re.search(regex_timedate, timedatectl_output)

                if not match:
                        logger.warning("No match to regex {} in {}".format(regex_timedate, timedatectl_output))
                        date_system = 'no_date'
                else:
                        # format YYYYMMDD_HHMM
                        date_system = "{}{}{}_{}{}".format(match.group(1), match.group(2), match.group(3), match.group(4), match.group(5))
                        logger.debug("system date: {}".format(date_system))
        except Exception as e:
                logger.exception("Exception \"{}\" during getting system time for file export.".format(e))
                date_system = 'no_date'

        # loop on different slots
        for device_info in device_infos:
                try:
                        slot = device_info[0]
                        device_name = re.sub('\W+','_', device_info[1].replace('(', '').replace(')', ''))
                        serial_number = device_info[2]

                        # build file path
                        folder_name = "{}_{}".format(device_name, serial_number)
                        folder_path = os.path.join(folder_path_base, folder_name)

                        # check if output folder is still there (can be unmounted if we write on a USB stick)
                        if not os.path.exists(folder_path_base):
                                exit(1)

                        # create the output folder if necessary
                        if not os.path.exists(folder_path):
                                os.makedirs(folder_path)
                except Exception as e:
                        logger.exception("Exception \"{}\" before export durint data preparation for device info {}.".format(e, device_info))
                        exit(1)

                # loop on the 2 type data and event to create all the files
                for handled_type in Log_type.DATA, Log_type.EVENT:
                        try:
                                type_as_num = 2 if handled_type == Log_type.DATA else 1
                                type_as_string = "Data" if handled_type == Log_type.DATA else "Event"

                                # Pidev (plugin devices) slot is always "20" by design and is managed separately
                                if slot != "20":
                                        # Manage regular slots here

                                        # build filename
                                        filename = "{}_{}_{}_log_{}.csv".format(device_name, serial_number, type_as_string, date_system).replace(' ', '_')

                                        file_path = os.path.join(folder_path, filename)

                                        # Creates log files
                                        if fake == True:
                                                f = open(file_path, "w")
                                                f.write("Fake {}s".format(type_as_string))
                                                f.close()
                                                logger.warning("Fake {} file {} created".format(type_as_string, file_path))
                                                time.sleep(1)
                                        else:
                                                # Read last data/events
                                                logger.debug("Read {}s for slot {}".format(type_as_string, slot))
                                                output = subprocess.check_output("TestClientII -Lrd0 -Y{} -h{}".format(type_as_num, slot), shell=True)
                                                logger.debug(output)
                                                # Export data/events as csv file on USB
                                                logger.info("Create file {}".format(file_path))
                                                output = subprocess.check_output("TestClientII -Lpr -Y{} -h{} -z{}".format(type_as_num, slot, file_path), shell=True)
                                                logger.debug(output)
                                elif not pidev_settings_exported:
                                        # Manage particular case of plugin devices where we want to export pidev files (like settings) to destination folder
                                        # Limitation: only single Pidev should be installed at a time as all pidev files would be exported for all Pidev
                                        # imports only for this particular case
                                        import glob
                                        import shutil
                                        logger.info("Export Pidev settings, slot number: {}".format(slot))
                                        # pidev files (like settings) are read from a subfolder and respect a specific pattern
                                        for pathname in glob.glob(os.path.join(pidev_export_path_base + '/**/*HL???_?????_*.csv')):
                                                # Add a timestamp at the end of the file name
                                                src_filename, src_file_extension = os.path.splitext(os.path.basename(pathname))
                                                dest_filename = "{}_{}{}".format(src_filename, date_system, src_file_extension)
                                                # In order to keep consistency with other exported files, HL???_????? is replaced by controller serial number
                                                dest_filename_with_serial = re.sub("HL\d\d\d_\d\d\d\d\d", serial_number, dest_filename)
                                                logger.info("copy file to {}".format(os.path.join(folder_path, dest_filename_with_serial)))
                                                shutil.copy(pathname, os.path.join(folder_path, dest_filename_with_serial))
                                        pidev_settings_exported = True

                        except Exception as e:
                                logger.exception("Exception \"{}\" during {} export for slot {}, go to next file".format(e, type_as_string, slot))
                                exit(1)
                
                try:
                        has_logger_file = device_has_logger_file(device_name)
                        # Export logger file specific to sensor (currently for Nitro only)
                        if logger_file_requested is True and has_logger_file is True:                 
                                file_number = logger_file_number_list[device_name]

                                # create the output folder if necessary
                                if not os.path.exists(folder_path):
                                    os.makedirs(folder_path)
                                
                                filename = "{}_{}_{}_{}".format(device_name, serial_number, "service_logger", date_system).replace(' ', '_')
                                sevice_logger_full_path = os.path.join(service_logger_export_path_base, folder_path)
                                service_logger_path = os.path.join(sevice_logger_full_path, filename)
                                logger.info("file_number {}".format(file_number))
                                logger.info("Create specific logger file {}".format(file_path))
                                output = subprocess.check_output("TestClientII -h{} -f{} -z {} -p".format(slot, file_number, service_logger_path), shell=True)
                                logger.debug(output)
                except Exception as e:
                        logger.exception("Exception \"{}\" during service logger file export for slot {}, go to next file".format(e, slot))
                        exit(1)
                
                # Flush the write to USB stick (fix FCON2-3456)
                lib_system.sync()


if __name__ == '__main__':

        logger = logging.getLogger()
        # Use syslog handler to have logs into journalctl
        lib_logger.add_handler_syslog('copy_logs')

        if len(sys.argv) < 2:
                print_usage()
                exit(1)

        # parse args
        try:
                opts, args = getopt.getopt(sys.argv[1:], "h", ["help", "logger-file=", "export-to=", "get-pidev-export-path"])

        except getopt.GetoptError:
                print("Unrecognized options ", sys.argv[1:])
                print_usage()
                exit(1)

        # scan args
        for opt, arg in opts:
                try:
                        if opt in ("-h", "--help"):
                                print_usage()
                                exit(0)
                        if opt in ("--logger-file"):
                                logger_file_requested = True
                                service_logger_export_path_base = arg
                        elif opt in ("--get-pidev-export-path"):
                                # simply print this path; directly consummed by backend
                                print(pidev_export_path_base)
                                exit(0)
                        elif opt in ("--export-to"):
                                export_to(arg)
                                exit(0)

                except Exception as e:
                        print("Exception thrown while executing the script")
                        print(e)
                        exit(2)

        print_usage()
        exit(1)
