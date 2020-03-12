# wifi-ap-manager
Managing WiFi Access Points on Raspberry Pi using a Python Script. Make sure to configure the SSID and passphrase at the top of the script before using it.
See https://www.mstriegel.de/Blog/2020-03_March.html#wifi-ap-with-python for more background information.

Tested and works on Ubuntu 18.04 and Raspbian on RasPi 3B+
## Usage
```Text
usage: wifi-ap-manager.py [-h] [-i] [-a] [-d] [-p] [-c]

Manage an access point on Raspi/Laptop

optional arguments:
  -h, --help           show this help message and exit
  -i, --interactive    Work in interactive mode instead of using commandline
                       script
  -a, --activate       Activate hostapd and dnsmasq. Only works if script has
                       been called with -p before
  -d, --deactivate
  -p, --prepare        Launch dhcpcd, as it takes longest.
  -c, --check_service

```

## TODO
Add Routing, Masquerade and Bridge Mode


## License
MIT