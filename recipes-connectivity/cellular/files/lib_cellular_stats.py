#!/usr/bin/python3
import os.path
import os
import sys
import time
import logging

from logging.handlers import RotatingFileHandler
from enum import Enum
from datetime import datetime
from lib_modem import ModemDiagnosticCode

date_format = '%Y/%m/%d %H:%M:%S'

logger = logging.getLogger(__name__)
# Add default empty logger to let the user of the library use it without logger defined
logger.addHandler(logging.NullHandler())

def __logModemStatCode(stat_code, signal_strength="N/A", tech="N/A"):
    """ Generic function to store a stat code (numeric value), signal strength (dBm) and technology (3G/4G/5G...) with date & time into an history file (CSV format).
        @stat_code: the code to log
        @signal_strength: the signal strength in dBm, or N/A as default (when signal_strength is not available yet)
        @tech: the technology, or N/A as default (when technology is not available yet)
        This CSV file is used for stats extraction & computation by a dedicated Excel tool
    """
    try:
        # log stat code with a timestamp
        date = datetime.now()
        date_str = date.strftime(date_format)
        utc_date = datetime.utcnow()
        utc_date_str = utc_date.strftime(date_format)
        #line formatted for CSV file (';' as delimiter)
        timezone = time.tzname[1] if time.localtime( ).tm_isdst==1 else time.tzname[0]
        line = '{};{};{};{};{};{}'.format(timezone, date_str, utc_date_str, stat_code, signal_strength, tech)
        csvlogger.info(line)
        logger.info("\"%s\" added to cellular CSV stats" % (line))
        return True
    except:
        pass
    return False

def logModemDiagnostic(modem_diagnostic_code, signal_strength="N/A", tech="N/A"):
    """ log a modem diagnostic code, the signal strength (dBm) and techonlogy (3G/4G/5G..) in the history file
        @modem_diagnostic_code: the code to log
        @signal_strength: the signal strength in dBm, or N/A as default (when signal_strength is not available yet)
        @tech: the technology, or N/A as default (when technology is not available yet)
    """
    if not isinstance(modem_diagnostic_code, ModemDiagnosticCode):
        return False

    # the first faulty diagnostic resets uptime counter, the first clean diagnostic starts uptime counter
    if modem_diagnostic_code == ModemDiagnosticCode.WellConfigured:
        logUptime()
    else:
        clearUpTime()

    # log the diagnostic code itself
    return __logModemStatCode(modem_diagnostic_code.value, signal_strength, tech)

class ExtentedModemStatCode(Enum):
    """ Additional modem stat code used to fill history CSV file
    """
    ModemDetection = -10
    ForcedModemReboot = -20

def logModemDetection():
    """ log a modem detection in the history file. Typically called when an usb modem device is detected in udev
    """
    return __logModemStatCode(ExtentedModemStatCode.ModemDetection.value)

def logForcedModemReboot():
    """ log a forced reboot of modem in the history file
    """
    return __logModemStatCode(ExtentedModemStatCode.ForcedModemReboot.value)

# file containing date & time of the initial successful modem configuration
uptime_file_path = "/tmp/cellular_data_supervisor_uptime"
def logUptime():
    """ log date & time of the initial successful modem configuration into a dedicated file.
    This file is used to compute uptime
    """
    # if the file exists, it means the initial successful modem configuration is already logged. Nothing to do
    if(os.path.isfile(uptime_file_path)):
        return
    try:
        # write the initial successful modem configuration date & time into the dedicated file.
        date = datetime.now()
        date_str = date.strftime(date_format)
        with open(uptime_file_path, 'w') as the_file:
            the_file.write(date_str)
        return
    except:
        pass

def computeUpTime():
    """ Return the current connectivity uptime in hours/minutes.
    Computation based on the initial successful modem configuration date & time saved into a dedicated file
    return 0 if the connectivity is down (in this case the file is absent)
    return -1 in case of error during computation
    """
    # if the file does not exist, it means the connectivity is down
    if(not os.path.isfile(uptime_file_path)):
        return 0
    try:
        # read the initial successful modem configuration date & time from the dedicated file and compute the duration
        with open(uptime_file_path, 'r') as the_file:
            line = the_file.readline()
            dt = datetime.strptime(line, '%Y/%m/%d %H:%M:%S')
            hours_decimal = round(((datetime.now()-dt).total_seconds()) / 3600, 2)
            hours = int(hours_decimal)
            minutes = (hours_decimal-hours)*0.6
            return round(hours + minutes, 2)
    except:
        pass
    return -1

def clearUpTime():
    """ Stops and reset connectivity uptime counter
    It simply deletes the file containing the initial successful modem configuration date & time
    """

    logger.info("")
    logger.info("-Remove uptime counter \"%s\"" % (uptime_file_path))

    try:
        os.remove(uptime_file_path)
    except:
        pass
    return


""" Create and configure a rotating logger to log all stats.
Stats are logged in stats_file_path. When file the size is about to be exceeded, the file is closed and a new file is silently opened.
The system will save old log files by appending the extensions .1
"""
# A do-nothing fallback handler used in case of exception creating a RotatingFileHandler
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

stats_file_path = "/media/persistent/system/cellular_data_supervisor_stats.csv"
# If the path of stats_file_path doesn't exist, create it
dir_name = os.path.dirname(stats_file_path)
if not os.path.exists(dir_name):
    os.makedirs(dir_name)

csvlogger = logging.getLogger('cellular_stats_logger')
# Disable propagate because this logger is only used to generate stats and is not expected to be forwarded to upper loggers
csvlogger.propagate = False
csvlogger.setLevel(logging.INFO)
try:
    # current log file is maximum 512Ko.
    # backup log file is 512Ko
    # 512Ko --> 2.5 months of history (~23 bytes/log. 1 log every 5 minutes)
    handler = RotatingFileHandler(stats_file_path, maxBytes=512*1024, backupCount=1)
except:
    handler = NullHandler()
csvlogger.addHandler(handler)

# Add log header if the file is missing or empty
new_log_file = (not os.path.isfile(stats_file_path) or os.path.getsize(stats_file_path) == 0)
if (new_log_file):
        csvlogger.info("Time zone;Local time;UTC time;Stat code; signal_strength (dBm); technology")
