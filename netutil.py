import network

wlan = network.WLAN(network.STA_IF)

def do_connect(ssid: str, key: str):

    wlan.active(True)
    if not wlan.isconnected():
        print("connecting to network...")
        wlan.connect(ssid, key)
        while not wlan.isconnected():
            pass
    return wlan.ifconfig()

def setup_time():
    import ntptime, time
    ntptime.settime()
    
    print(time.localtime())