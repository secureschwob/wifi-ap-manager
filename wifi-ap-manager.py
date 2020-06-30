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
# Script for installing and configuring Ubuntu/Debian DHCP server and wireless access points.
#
# Essentially performs the steps from
# https://www.raspberrypi.org/documentation/configuration/wireless/access-point-routed.md (Dated 2020-06-08)
# in a clean, easily reversible and automated way
######

# Standard library imports
import argparse
from configparser import ConfigParser   
import os
import shutil
import subprocess
import sys
# import time



###
# Global variables - do not modify here, use config.ini instead.
###
CONFIG_PARSER = None
PLATFORM:str = None

ETHERNET_INTERFACE = ""
WIFI_INTERFACE = ""
WIFI_DRIVER = ""
ACCESSPOINT_SSID = ""
ACCESSPOINT_PW = ""
IP_ADDRESS = ""
DCHP_IP_RANGE_LOWER = ""
DHCP_IP_RANGE_UPPER = ""

SYSTEM_CONFIG_FILES = {
    "dhcp_config_file_path":        "/etc/dhcpcd.conf",
    "dnsmasq_config_file_path":     "/etc/dnsmasq.conf", 
    "hostapd_config_file_path":     "/etc/hostapd/hostapd.conf",
    "hostapd_link_to_config_file":  "/etc/default/hostapd",
    "hostapd_init_d_file":          "/etc/init.d/hostapd",
    "routed_ap_config_file":        "/etc/sysctl.d/routed-ap.conf"
    }

DEPENDENCIES=("hostapd", "dnsmasq", "dhcpcd5")
SERVICE_LIST=["hostapd", "dnsmasq", "dhcpcd"]



###
# Functions
###
def parse_commandline_arguments():
    """
    Add commandline options to the program
    """
    parser = argparse.ArgumentParser(
        description="Manage an access point on Raspi/Laptop")
    parser.add_argument('-c', '--configfile', metavar='configFile',
                        help="Location of the config file. If empty, the default location \'./config.ini\' will be used")

    parser.add_argument('-p', "--prepare", help="Prepare dhcpcd, as it takes longest. Then call this script with -a to activate hostapd and dnsmasq.", action='store_true')
    parser.add_argument('-a', "--activate", help="Activate hostapd and dnsmasq. Only works if dhcpcd has been set up with -p before.", action='store_true')
    parser.add_argument('-aa', "--activate_all", action='store_true', help="Activate dhcpcd, hostapd and dnsmasq in a single run.")
    parser.add_argument('-d', "--deactivate_all", action='store_true', help='Deactivate dhcpcd, dnsmasq, hostapd and restore their default configurations.')
    # parser.add_argument('-r', "--routing", action='store_true', help="Enable routing between interfaces")

    parser.add_argument('-checkdep', "--check_dependencies", action='store_true', help="Check if dependencies are installed.")
    parser.add_argument('-i', "--install_dependencies", action='store_true', help="Install missing dependencies.")
    parser.add_argument('-checkdaemon', "--check_daemon_status", action='store_true', help="Check status of dhcpcd, dnsmasq and hostapd daemons.")
    
    parser.add_argument('-ethbridge', "--dhcp_at_ethernet_interface", action='store_true', help="Provide an IP address at the Ethernet interface.")
    args = parser.parse_args()
    return args



def get_config_parser_and_read_config_file(path='config.ini'):
    """
    Return parser so that configuration file can be used in other files

    Keyword arguments:
    path (type:string) -- path to config file. Default set to ./config.ini
    """
    global CONFIG_PARSER

    parser = ConfigParser()

    if parser.read(path) == []:
        sys.exit("\nCould not load a config file. Exiting.")
    else:
        CONFIG_PARSER = parser



def get_settings_from_config_file():
    """ Using config parser, read the settings from the config.ini file into variables """

    if CONFIG_PARSER == None:
        sys.exit("\There is no configparser. Exiting.")

    global ETHERNET_INTERFACE
    ETHERNET_INTERFACE = CONFIG_PARSER.get("network_interfaces", "ETHERNET_INTERFACE")
    global WIFI_INTERFACE
    WIFI_INTERFACE = CONFIG_PARSER.get("network_interfaces", "WIFI_INTERFACE")          
    global WIFI_DRIVER
    WIFI_DRIVER = CONFIG_PARSER.get("network_interfaces", "WIFI_DRIVER")
    global ACCESSPOINT_SSID
    ACCESSPOINT_SSID = CONFIG_PARSER.get("access_point_settings", "ACCESSPOINT_SSID")
    global ACCESSPOINT_PW
    ACCESSPOINT_PW = CONFIG_PARSER.get("access_point_settings", "ACCESSPOINT_PW")
    global IP_ADDRESS
    IP_ADDRESS = CONFIG_PARSER.get("access_point_settings", "IP_ADDRESS")
    global DCHP_IP_RANGE_LOWER
    DCHP_IP_RANGE_LOWER = CONFIG_PARSER.get("access_point_settings", "DCHP_IP_RANGE_LOWER")
    global DHCP_IP_RANGE_UPPER
    DHCP_IP_RANGE_UPPER = CONFIG_PARSER.get("access_point_settings", "DHCP_IP_RANGE_UPPER")



def clean_exit():
    all_()
    sys.exit(0)



def check_and_install_all_dependencies():
    for dependency in DEPENDENCIES:
        if check_if_installed(dependency) == False:
            install_dependency(dependency)


def check_if_installed(dependency) -> bool:
    args = ["whereis", dependency]
    command_subprocess = subprocess.Popen(args, stdout=subprocess.PIPE)
    command_output, _ = command_subprocess.communicate()

    if command_output == b'':
        return False
    else:
        return True


def install_dependency(dependency):
    print(f"Updating apt, then installing dependency {dependency}")
    subprocess.run(["apt", "update"])
    subprocess.run(["apt", "upgrade"])
    subprocess.run(["apt", "install", dependency])



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



def backup_system_config_files():
    """ Make a backup copy of files we are going to modify for setting up WiFi AP and DHCP server
	NOTE if your original config file is screwed up already, your backup will be screwed up, too
    """
    for _key, configfile in SYSTEM_CONFIG_FILES.items():
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
    """ Replace the modified config files with the backup copies taken of unaltered files 
    """
    for _key, configfile in SYSTEM_CONFIG_FILES.items():
        configfile_original = configfile + "_original"

        if os.path.exists(configfile_original):
            shutil.copyfile(configfile_original, configfile)
            os.remove(configfile_original)
            print(f"Restored backup {configfile}")

    # as this file is only needed for our program, we simply delete it and do not have to restore a backup
    if os.path.exists(SYSTEM_CONFIG_FILES["routed_ap_config_file"]):
        os.remove(SYSTEM_CONFIG_FILES["routed_ap_config_file"])
        print("Deleted {}".format(SYSTEM_CONFIG_FILES["routed_ap_config_file"]))



def prepare_dhcpcd(network_interface):
    """  Restarting dhcpcd is really slow. Thus, call this function initially to set up everything except hostapd.  
    """
    print("Preparing dhcpcd")

    # stop_network_manager()
    stop_dnsmasq()
    stop_hostapd()
       
    configure_dhcpcd(network_interface)

    restart_dhcpd()

    check_all_daemon_statuses()



def start_hostapd_and_dnsmasq(network_interface):
    # need to have that in one function as the sequence
    # of activation matters
    configure_hostapd()
    start_hostapd()

    configure_dnsmasq(network_interface)
    restart_dnsmasq()



def deactivate_all_and_restore_system_config():
    print("Deactivating...")
    stop_dhcpcd()
    stop_dnsmasq()
    stop_hostapd()
    #start_network_manager()
    restore_config_backup_files()



def restart_dhcpd():
    dhcpd_restart_args = ["sudo", "service", "dhcpcd", "restart"]
    subprocess.run(dhcpd_restart_args)


def stop_dhcpcd():
    dhcpd_stop_args = ["sudo", "service", "dhcpcd", "stop"]
    subprocess.run(dhcpd_stop_args)



def stop_dnsmasq():
    dnsmasq_stop_args = ["sudo", "systemctl", "stop", "dnsmasq"]
    subprocess.run(dnsmasq_stop_args)


def restart_dnsmasq():
    dnsmasq_restart_args = ["sudo", "service", "dnsmasq", "restart"]
    subprocess.run(dnsmasq_restart_args)



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



def configure_dhcpcd(network_interface: str):
    """ Set a static IP address to the network interface provided as argument """
    iface = network_interface.replace('"', '')
    ip = IP_ADDRESS.replace('"', '')

    static_ip_append_string=f"\
interface {iface}\n\
    static ip_address={ip}/24\n\
    nohook wpa_supplicant"

    with open(SYSTEM_CONFIG_FILES["dhcp_config_file_path"], 'a') as file:
        file.write(static_ip_append_string)



def configure_dnsmasq(network_interface: str):
    """
    Configure dnsmasq on the given network interface

    Keyword arguments:
        network_interface -- e.g. your WiFi or Ethernet interface
    
    NOTE: dhcp-authoritative following https://raspberrypi.stackexchange.com/questions/33946/dnsmasq-dhcp-not-giving-ip-address
    """
    iface = network_interface.replace('"', '')
    ip_range_lower = DCHP_IP_RANGE_LOWER.replace('"', '')
    ip_range_upper = DHCP_IP_RANGE_UPPER.replace('"', '')

    configure_dnsmasq_append_string=f"\
interface={iface}\n\
dhcp-authoritative\n\
dhcp-range={ip_range_lower},{ip_range_upper},255.255.255.0,24h"

    with open(SYSTEM_CONFIG_FILES["dnsmasq_config_file_path"],'a') as file:
        file.write(configure_dnsmasq_append_string)



def configure_hostapd():
    """
    As we can use hostapd on the WiFi interface only, no need to provide it as argument.  
    NOTE: https://raspberrypi.stackexchange.com/questions/82614/ap-setup-from-documentation-not-working
    """
    iface = network_interface.replace('"', '')

    configure_hostapd_append_string=f"\
interface={iface}\n\
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

    with open(SYSTEM_CONFIG_FILES["hostapd_config_file_path"], 'w') as file:
        file.write(configure_hostapd_append_string)


    config_location_path="DAEMON_CONF=\"" + SYSTEM_CONFIG_FILES["hostapd_config_file_path"] + "\"" 

    # FIXME write instead of append, append causes multiple appends - why?   
    with open(SYSTEM_CONFIG_FILES["hostapd_link_to_config_file"], 'w') as file:
        file.write(config_location_path)
    
    # search and replace in file
    config_location_path_no_quot_marks="DAEMON_CONF=" + SYSTEM_CONFIG_FILES["hostapd_config_file_path"]
    with open(SYSTEM_CONFIG_FILES["hostapd_init_d_file"]) as file:
        new_text = file.read().replace("DAEMON_CONF=", config_location_path_no_quot_marks)

    with open(SYSTEM_CONFIG_FILES["hostapd_init_d_file"], 'w') as file:
        file.write(new_text)



# def configure_routing(output_interface: str):
#     """
#     Keyword Arguments:
#         output_interface -- if set to e.g., the WiFi interface, packets received via Ethernet will be forwarded to WiFi
#     """
#     configure_routing_string = "net.ipv4.ip_forward=1"

#     with open(SYSTEM_CONFIG_FILES["routed_ap_config_file"], 'a') as file:
#         file.write(configure_routing_string)

#     outif = output_interface.replace('"', '')
#     args = ["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", outif, "-j", "MASQUERADE"]
#     command_subprocess = subprocess.Popen(args, stdout=subprocess.PIPE)

#     print(f"Routing incoming traffic to interface {outif}")




if __name__ == "__main__":
    if not os.geteuid() == 0:
        sys.exit("Please run this program with root privileges.")

    args = parse_commandline_arguments()
    get_config_parser_and_read_config_file()
    get_settings_from_config_file()


    if args.prepare:
        if os.path.exists(".ap_is_prepared_marker"):
            sys.exit("dhcpcd is already prepared, now call script with -a to launch access point")
            
        backup_system_config_files()
        _ = open(".ap_is_prepared_marker", 'a')
        prepare_dhcpcd(WIFI_INTERFACE)
        print("dhcpcd is prepared, now call script with -a to launch access point")
    
    elif args.activate:
        if not os.path.exists(".ap_is_prepared_marker"):
            sys.exit("Please call this script with -p first to prepare the access point.")
        else:
            if not os.path.exists(".ap_is_running_marker"):
                _ = open(".ap_is_running_marker", 'a')
                start_hostapd_and_dnsmasq(WIFI_INTERFACE)

                # if args.routing:
                #     configure_routing(output_interface=ETHERNET_INTERFACE)
    
    elif args.activate_all:
        if os.path.exists(".ap_is_prepared_marker") and os.path.exists(".ap_is_running_marker"):
            sys.exit("Wireless AP is already running.")
        else:
            _ = open(".ap_is_prepared_marker", 'a')
            _ = open(".ap_is_running_marker", 'a')
            backup_system_config_files()
            prepare_dhcpcd(WIFI_INTERFACE)
            start_hostapd_and_dnsmasq(WIFI_INTERFACE)

            # if args.routing:
            #     configure_routing(output_interface=ETHERNET_INTERFACE)
    
    elif args.deactivate_all:
        deactivate_all_and_restore_system_config()
        try:
            os.remove(".ap_is_prepared_marker")
            os.remove(".ap_is_running_marker")
        except FileNotFoundError:
            print("Tried to deactivate, but apparently nothing was running.")
    
    elif args.check_dependencies:
        for dependency in DEPENDENCIES:
            if check_if_installed(dependency) == False:
                print(f"Dependency {dependency} missing.")
        print("Dependency check done. If nothing was printed, all dependencies are installed.")
    
    elif args.install_dependencies:
        check_and_install_all_dependencies()
        print("Dependency install done. If nothing was printed, all dependencies were installed already.")
    
    elif args.check_daemon_status:
        check_all_daemon_statuses()
    
    elif args.dhcp_at_ethernet_interface:
        if os.path.exists(".ap_is_prepared_marker") and os.path.exists(".ap_is_running_marker"):
            sys.exit("DHCP is already running at Ethernet interface.")
        else:
            _ = open(".ap_is_prepared_marker", 'a')
            _ = open(".ap_is_running_marker", 'a')
            backup_system_config_files()
            prepare_dhcpcd(ETHERNET_INTERFACE)
            configure_dnsmasq(ETHERNET_INTERFACE)
            restart_dnsmasq()

            # if args.routing:
            #     configure_routing(output_interface=WIFI_INTERFACE)
    else:
        sys.exit("Please specify one argument. Call this script with --help to see supported arguments.")