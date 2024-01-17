#!/usr/bin/python3
import sys
import json

# Replace license file path with its content, this way the license json file will contain all mandatory data
with open(sys.argv[1], 'r+', encoding='iso-8859-1') as license_json_file:
    license_info = json.load(license_json_file)
    for node in license_info:
        for info in license_info[node]:
            if info == 'licenseFile':
                with open(license_info[node]['licenseFile'], 'r+',encoding='iso-8859-1') as content:
                    file_data = content.read()
                    license_info[node]['licenseFile']=file_data
                    license_json_file.seek(0)
                    json.dump(license_info, license_json_file, indent=4)
                    license_json_file.truncate()

