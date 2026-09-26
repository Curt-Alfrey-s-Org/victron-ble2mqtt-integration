# USB Bluetooth dongle: `.229` → HA VM 105

Official: [USB Devices in Virtual Machines](https://pve.proxmox.com/wiki/USB_Devices_in_Virtual_Machines), [HA Bluetooth](https://www.home-assistant.io/integrations/bluetooth/).

`.105` is Proxmox **VM 105** on `.229`. Pass the dongle into that VM. Do **not** pass Pi 4's Victron stick (`2357:0604`). Do **not** run `qm set` until `lsusb` shows the new device.

## When the stick is plugged into `.229`

```bash
ssh root@192.168.0.229
lsusb
# Record VID:PID of the NEW adapter. Skip 2357:0604.
qm config 105 | grep -i usb
qm set 105 -usb0 host=VID:PID
# If usb0 is taken: -usb1, -usb2, ...
```

On `.105`:

```bash
ls /sys/class/bluetooth
hciconfig
sudo docker exec homeassistant ls /sys/class/bluetooth
```

If the VM sees `hci*` and the container does not, add that device to the HA compose and recreate the container. HA Bluetooth should then list the adapter. Ads only until we add `ha-105` to heard-by.

Do not start a Govee GATT bridge on this radio in this checkpoint.
