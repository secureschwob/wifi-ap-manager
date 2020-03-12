# Copyright 2020-03 Martin Striegel

# Permission is hereby granted, free of charge, to any person obtaining a copy of 
# this software and associated documentation files (the "Software"), to deal in 
# the Software without restriction, including without limitation the rights to use, 
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the 
# Software, and to permit persons to whom the Software is furnished to do so, 
# subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR 
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, 
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.

######
# @file		wifi-ap-manager.py
# @author	Martin Striegel
#			mail@mstriegel.de
# Script for installing and configuring Ubuntu/Debian as WiFi access point with
# a DHCP server.
#
# Essentially performs the steps from
# https://www.raspberrypi.org/documentation/configuration/wireless/access-point.md
# in a clean and automated way
######

# Standard library imports
import argparse
import os
import shutil
import subprocess
import sys
import time



###
# Global variables
###
# configure your network here
WIFI_INTERFACE = "wlp4s0"   # @Raspi: "wlan0"
WIFI_DRIVER = "nl80211"     # @Raspi: "n 80211"
ACCESSPOINT_SSID = "yourssid"
ACCESSPOINT_PW = "yourpassword"
IP_ADDRESS="192.168.52.1"
DCHP_IP_RANGE_LOWER="192.168.52.2"
DHCP_IP_RANGE_UPPER="192.168.52.20"


#do not modify
PLATFORM:str = None
CONFIG_FILES = {
    "dhcp_config_file_path":        "/etc/dhcpcd.conf",
    "dnsmasq_config_file_path":     "/etc/dnsmasq.conf", 
    "hostapd_config_file_path":     "/etc/hostapd/hostapd.conf",
    "hostapd_link_to_config_file":  "/etc/default/hostapd",
    "hostapd_init_d_file":          "/etc/init.d/hostapd",
    }
DEPENDENCIES=("hostapd", "dnsmasq", "dhcpcd5")
SERVICE_LIST=["hostapd", "dnsmasq", "dhcpcd", "NetworkManager"]
AP_IS_RUNNING = False


###
# Functions
###
def parse_arguments():
    """
    Add commandline options to the program
    """
    parser = argparse.ArgumentParser(
        description="Manage an access point on Raspi/Laptop")
    parser.add_argument('-i', '--interactive', 
        help="Work in interactive mode instead of using commandline script", action='store_true')
    parser.add_argument('-a', "--activate", help="Activate hostapd and dnsmasq. Only works if script has been called with -p before", action='store_true')
    parser.add_argument('-d', "--deactivate", action='store_true')
    parser.add_argument('-p', "--prepare", help="Launch dhcpcd, as it takes longest.", action='store_true')
    parser.add_argument('-c', "--check_service", action='store_true')
    args = parser.parse_args()
    return args



def show_commands():
    print("Press a number to choose:\n \
            1: Install needed programs\n \
            2: Activate AP+DHCP\n \
            3: Deactivate AP+DHCP\n \
            4: Check AP+DHCP status\n \
            5: Deactivate and quit\n \
            6: Show supported commands")



def clean_exit():
    deactivate_ap_and_dhcp()
    sys.exit(0)



def check_and_install_all_dependencies():
    for dependency in DEPENDENCIES:
        install_program(dependency)



def install_program(dependency):
    if check_if_installed(dependency) == True:
        return True

    print(f"Updating apt, then installing dependency {dependency}")
    subprocess.run(["apt", "update"])
    subprocess.run(["apt", "upgrade"])
    subprocess.run(["apt", "install", dependency])



def check_if_installed(dependency) -> bool:
    args = ["which", dependency]
    command_subprocess = subprocess.Popen(args, stdout=subprocess.PIPE)
    command_output, _ = command_subprocess.communicate()

    if command_output == b'':
        return False
    else:
        return True



def backup_config_files():
    # Make a backup copy of file we are going to modify for setting up WiFi AP
	# and DHCP server
    #
	# NOTE if your original config file is screwed up already, your backup will
	# 	be screwed up, too
    
    for _key, configfile in CONFIG_FILES.items():
        configfile_original = configfile + "_original"

        if os.path.exists(configfile):
            if not os.path.exists(configfile_original):
                shutil.copyfile(configfile, configfile_original)
                print(f"Created copy of file {configfile} named {configfile_original}")
            else:
                print(f"Found backup file {configfile_original}. No need to backup.")
        else:
            print(f"File {configfile} not found, ignoring it.")



def restore_config_backup_files():
	# Replace the modified config files with the backup copies taken of unaltered
	# files
    for _key, configfile in CONFIG_FILES.items():
        configfile_original = configfile + "_original"

        if os.path.exists(configfile_original):
            shutil.copyfile(configfile_original, configfile)
            os.remove(configfile_original)
            print(f"Restored backup if {configfile}")



def prepare_all_except_hostapd_and_dnsmasq():
    """ restarting dhcpcd is really slow. Thus, call this function initially 
    to set up everything except hostapd.  """
    print("Preparing all except for hostapd...")
    backup_config_files()

    stop_network_manager()
    stop_dnsmasq()
    stop_hostapd()
       

    set_static_ip()

    restart_dhcpd()

    # done in start_hostapd_and_dnsmasq()
    # configure_dnsmasq()
    # restart_dnsmasq()

    check_all_daemon_statuses()



def start_hostapd_and_dnsmasq():
    # need to have that in one function as the sequence
    # of activation matters
    configure_hostapd()
    start_hostapd()

    configure_dnsmasq()
    restart_dnsmasq()



def activate_ap_and_dhcp():
    """ Slow variant, as restarting dhcpcd takes ages
    TODO check if dependencies are installed
    """
    print("Activating...")
    backup_config_files()

    stop_network_manager()
    stop_dnsmasq()
    stop_hostapd() 

    set_static_ip()

    restart_dhcpd()

    configure_hostapd()
    start_hostapd()

    # one must activate dnsmasq after hostapd
    configure_dnsmasq()
    restart_dnsmasq()

    check_all_daemon_statuses()



def deactivate_ap_and_dhcp():
    print("Deactivating...")
    stop_dhcpcd()
    stop_dnsmasq()
    stop_hostapd()
    start_network_manager()
    restore_config_backup_files()
    check_all_daemon_statuses()



def configure_dnsmasq():
    # dhcp-authoritative nach https://raspberrypi.stackexchange.com/questions/33946/dnsmasq-dhcp-not-giving-ip-address
    configure_dnsmasq_append_string=f"\
interface={WIFI_INTERFACE}\n\
    dhcp-authoritative\n\
    dhcp-range={DCHP_IP_RANGE_LOWER},{DHCP_IP_RANGE_UPPER},255.255.255.0,24h"

    with open(CONFIG_FILES["dnsmasq_config_file_path"],'w') as file:
        file.write(configure_dnsmasq_append_string)



def stop_dnsmasq():
    dnsmasq_stop_args = ["sudo", "systemctl", "stop", "dnsmasq"]
    subprocess.run(dnsmasq_stop_args)



def restart_dnsmasq():
    dnsmasq_restart_args = ["sudo", "service", "dnsmasq", "restart"]
    subprocess.run(dnsmasq_restart_args)



def configure_hostapd():
    # https://raspberrypi.stackexchange.com/questions/82614/ap-setup-from-documentation-not-working

    configure_hostapd_append_string=f"\
interface={WIFI_INTERFACE}\n\
driver={WIFI_DRIVER}\n\
ssid={ACCESSPOINT_SSID}\n\
hw_mode=g\n\
channel=7\n\
wmm_enabled=0\n\
macaddr_acl=0\n\
auth_algs=1\n\
ignore_broadcast_ssid=0\n\
wpa=2\n\
wpa_passphrase={ACCESSPOINT_PW}\n\
wpa_key_mgmt=WPA-PSK\n\
wpa_pairwise=TKIP\n\
rsn_pairwise=CCMP"

    
    with open(CONFIG_FILES["hostapd_config_file_path"], 'w') as file:
        file.write(configure_hostapd_append_string)


    config_location_path="DAEMON_CONF=\"" + CONFIG_FILES["hostapd_config_file_path"] + "\"" 

    # FIXME write instead of append, append causes multiple appends - why?   
    with open(CONFIG_FILES["hostapd_link_to_config_file"], 'w') as file:
        file.write(config_location_path)
    
    # search and replace in file
    config_location_path_no_quot_marks="DAEMON_CONF=" + CONFIG_FILES["hostapd_config_file_path"]
    with open(CONFIG_FILES["hostapd_init_d_file"]) as file:
        new_text = file.read().replace("DAEMON_CONF=", config_location_path_no_quot_marks)

    with open(CONFIG_FILES["hostapd_init_d_file"], 'w') as file:
        file.write(new_text)



def start_hostapd():
    unmask_command = ["sudo", "systemctl", "unmask", "hostapd"]
    enable_command = ["sudo", "systemctl", "enable", "hostapd"]
    start_command = ["sudo", "systemctl", "start", "hostapd"]
    subprocess.run(unmask_command)
    subprocess.run(enable_command)
    subprocess.run(start_command)



def stop_hostapd():
    hostapd_stop_args = ["sudo", "systemctl", "stop", "hostapd"]
    subprocess.run(hostapd_stop_args)



def start_network_manager():
    network_manager_start_command = ["sudo", "service", "NetworkManager", "start"]
    subprocess.run(network_manager_start_command)



def stop_network_manager():
    network_manager_stop_args = ["sudo", "service", "NetworkManager", "stop"]
    subprocess.run(network_manager_stop_args)



def restart_dhcpd():
    dhcpd_restart_args = ["sudo", "service", "dhcpcd", "restart"]
    subprocess.run(dhcpd_restart_args)



def stop_dhcpcd():
    dhcpd_stop_args = ["sudo", "service", "dhcpcd", "stop"]
    subprocess.run(dhcpd_stop_args)



def check_all_daemon_statuses():
    print("Checking daemon statuses:")
    for _, service in enumerate(SERVICE_LIST):
        check_daemon_status(service)



def check_daemon_status(service):
    check_command = ["sudo", "service", service, "status"]
    command_subprocess = subprocess.Popen(check_command, stdout=subprocess.PIPE)
    command_output, _ = command_subprocess.communicate()
    output_string = command_output.decode('utf-8')

    active_string = "Active: active (running)"
    failed_string = "Active: failed"
    inactive_string = "Active: inactive (dead)"
    if active_string in output_string:
        print(f"{service}: {active_string}")
    elif failed_string in output_string:
        print(f"{service}: {failed_string}")
    elif inactive_string in output_string:
        print(f"{service}: {inactive_string}")
    else:
        print(f"{service}: strange status")




def set_static_ip():
    static_ip_append_string=f"\
interface {WIFI_INTERFACE}\n\
    static ip_address={IP_ADDRESS}/24"

    with open(CONFIG_FILES["dhcp_config_file_path"], 'a') as file:
        file.write(static_ip_append_string)
   


def interactive_run():
    global AP_IS_RUNNING
    keyboard_character_getter = _Getch()

    show_commands()

    while True:
        read_character = keyboard_character_getter()
        if read_character == '1':
            check_and_install_all_dependencies()
        elif (read_character == '2') and (AP_IS_RUNNING == False):
            activate_ap_and_dhcp()
            AP_IS_RUNNING = True
        elif read_character == '3':
            deactivate_ap_and_dhcp()
            AP_IS_RUNNING = False
        elif read_character == '4':
            check_all_daemon_statuses()
        elif read_character == '5':
            clean_exit()
        elif read_character == '6':
            show_commands()





if __name__ == "__main__":
    if not os.geteuid() == 0:
        sys.exit("Please run this program with root privileges.")

    args = parse_arguments()

    if args.prepare:
        prepare_all_except_hostapd_and_dnsmasq()
        _ = open(".ap_is_prepared_marker", 'a')
        print("All set up, now call script with -a to launch access point")
    elif args.activate:
        if not os.path.exists(".ap_is_prepared_marker"):
            sys.exit("Please call this script with -p first to prepare the access point.")
        start_hostapd_and_dnsmasq()
    elif args.deactivate:
        deactivate_ap_and_dhcp()
        os.remove(".ap_is_prepared_marker")
    elif args.interactive:
        from getch import _Getch
        interactive_run()
    elif args.check_service:
        check_all_daemon_statuses()
    else:
        sys.exit("Please specify one argument. Call this script with --help to see supported arguments.")