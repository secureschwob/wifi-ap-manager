# wifi-ap-manager
Managing WiFi Access Points on Raspberry Pi using a Python Script. Make sure to configure network information in `example_config.ini`.
See [my blog](https://www.mstriegel.de/Blog/2020-03_March.html#wifi-ap-with-python) for background information.

Tested and works on Ubuntu 19.10, 18.04 and Raspbian on RasPi 3B+


## Preparation
On Ubuntu 19.10, `systemd-resolve` blocks part 53 which is needed by `dnsmasq`. Do the following [1]:
```Bash
sudo lsof -i -P -n | grep LISTEN  # to check that indeed systemd-resolve listens on port 53
sudo systemctl stop systemd-resolved

# as superuser, edit systemd-resolve configuration in /etc/systemd/resolved.conf so it looks like below. I think DNSStubListener causes port 53 to be blocked
DNS=8.8.8.8
FallbackDNS=
MulticastDNS=no
DNSSEC=no
DNSOverTLS=no
DNSStubListener=no

# now create a symlink to /etc/resolv.conf, then restart systemd-resolved:
sudo ln -sf /run/systemd/resolve/resolv.conf /etc/resolv.conf
sudo systemctl start systemd-resolved
```

Use the Python script to check missing dependencies:
```Bash
usage: wifi-ap-manager.py -checkdep
```

## Run it
For example, use
```Bash
sudo python3 wifi-ap-manager.py -aa
```
to configure and activate all daemons in one run. This takes a while, as we have to wait for `dhcpcd` to restart, which is pretty slow.

If you need to quickly toggle an wireless access point on and off, do this:
```Bash
sudo python3 wifi-ap-manager.py -p  # for preparing dhcpcd, call this e.g. directly after launching your raspberry pi
sudo python3 wifi-ap-manager.py -a  # to actually activate the access point
```




## TODO
* WirelessAP testing
* Error handling in case script is called with `-a` or `-aa` twice
* Add Routing, Masquerade and Bridge Mode


## License
MIT



## References
* [1] https://jonamiki.com/2020/01/29/dnsmasq-failed-to-create-listening-socket-for-port-53-address-already-in-use/