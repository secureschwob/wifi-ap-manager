# wifi-ap-manager
Managing WiFi Access Points on Raspberry Pi using a Python Script. Make sure to configure network information in `example_config.ini`.
See [my blog](https://www.mstriegel.de/Blog/2020-03_March.html#wifi-ap-with-python) for background information.

Tested and works on Ubuntu 19.10, 18.04 and Raspbian on RasPi 3B+


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
sudo python3 wifi-ap-manager.py -p  # for preparing dhcpcd, call this e.g. directly after booting your Raspberry Pi
sudo python3 wifi-ap-manager.py -a  # to actually activate the access point quickly
```


## TODO
* WirelessAP testing
* Add Routing, Masquerade and Bridge Mode - while some is already implemented, does not work yet. Follow this? https://help.ubuntu.com/community/Internet/ConnectionSharing


## License
MIT



## References
* [1] https://jonamiki.com/2020/01/29/dnsmasq-failed-to-create-listening-socket-for-port-53-address-already-in-use/