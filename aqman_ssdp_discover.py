import requests as requests
import socket
import json
import struct
import time
import netifaces
import fcntl
import subprocess
import asyncio
from ast import literal_eval



SERVICE_PORT = 8297
global flag
flag = 1



async def _process_async():
    time.sleep(3)
    global flag
    flag = 0
    time.sleep(5)
    flag = 1



async def process_async():
    await _process_async()



def parse_headers(response, convert_to_lowercase=True):
    """
    Receives an HTTP response/request bytes object and parses the HTTP headers.
    Return a dict of all headers.
    If convert_to_lowercase is true, all headers will be saved in lowercase form.
    """

    valid_headers = (
        b"NOTIFY * HTTP/1.1\r\n",
        b"M-SEARCH * HTTP/1.1\r\n",
        b"HTTP/1.1 200 OK\r\n",
    )

    if not any([response.startswith(x) for x in valid_headers]):
        raise ValueError(
            "Invalid header: Should start with one of: {}".format(valid_headers)
        )

    lines = response.split(b"\r\n")
    headers = {}

    # Skip the first line since it's just the HTTP return code

    for line in lines[1:]:
        if not line:
            break  # Headers and content are separated by a blank line
        if b":" not in line:
            raise ValueError("Invalid header: {}".format(line))
        header_name, header_value = line.split(b":", 1)
        headers[header_name.decode("utf-8").lower().strip()] = header_value.decode(
            "utf-8"
        ).strip()
    return headers


def create_msearch_payload(host, st, mx=1):
    data = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST:{}\r\n"
        'MAN: "ssdp:discover"\r\n'
        "ST:{}\r\n"
        "MX:{}\r\n"
        "\r\n"
    ).format(host, st, mx)
    
    return data.encode("utf-8")


def discover(service, timeout=1, retries=20, mx=5):
    host = "{}:{}".format("239.255.255.250", 1900)
    message = create_msearch_payload(host, service, mx)
    group = ("239.255.255.250", 1900)
    """
    message = "\r\n".join([
        'M-SEARCH * HTTP/1.1',
        'HOST: "239.255.255.250:1900"',
        'MAN: "ssdp:discover"',
        'NT: "ssdp:all"',
        'MX: "1"'])
    print(message)
    """

    for _ in range(retries):
        responses = []
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        except Exception as e:
            print("error message: ",e)
            sock.close()
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            print("close the last socket and creating new one")

            
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(timeout)
        sock.sendto(message, group)
        #data=sock.recv(1024)
        cnt = 0
        while cnt<50:
            try:
                data = sock.recv(1024)
                break

            except Exception as e:
                cnt+=1
                print("error..{0} try again {1}".format(e,cnt))


        responses.append(data)
       
        parsed_responses = []

        for response in responses:

            try:
                headers = parse_headers(response)
                parsed_responses.append(headers)
            except ValueError:
                # Invalid response, do nothing.
                # TODO: Log dropped responses
                pass
            except AttributeError:
                # Happens when there is no response from ssdp servers
                pass

    return parsed_responses



def get_uart_server():
    ssdps = discover("ssdp:kictechaqman")
    print("Found SSDP Services...")
    print("ssdps:",ssdps)
    for ssdp in ssdps:
        if ssdp['usn'] == 'hass-aqman-server':
            return ssdp['location']



def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(
        fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24]
    )


def get_interfaces(): #get_ifnames
    out = subprocess.Popen(['cat', '/proc/net/dev'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = out.communicate()
    stdout = stdout.decode('utf-8')
    l = stdout.split('\n')
    interfaces = []

    for interface in l[2:]:
        iface = interface.split(":")[0]
        if iface != "":
            interfaces.append(iface.strip())   
    return interfaces



async def post_network_data():

    print("come into post_network_data")
    for interface in get_interfaces():
        if interface[0] == 'e':
            ip_address = get_ip_address(interface)
            break

        elif 'wlan' in interface:
            ip_address = get_ip_address(interface)

    #uart_server_address = uart_server_url['ip']
    network_interface = netifaces.interfaces()
    #print(network_interface)
    network_info ={}

    #network_temp = netifaces.ifaddresses(network_interface[4])[2][0]
    #print(netifaces.ifaddresses(network_interface[4]))
    #network_info['ip'] = network_temp['addr']
    #network_info['gateway'] = netifaces.gateways()['default'][2][0]
    #network_info['netmask'] = network_temp['netmask']
    #network_info['nameserver'] = nameserver
    #network_info['sn'] = AQMSERIAL
    #network_info['port'] = str(SERVICE_PORT)


    uart_server_url = get_uart_server()
    go_server_url = "http://"+str(ip_address)+":"+str(SERVICE_PORT)+ "/api/device/"
    print("uart_server_url: ",uart_server_url)
    uart_server_url = literal_eval(uart_server_url)
    go_server_url = go_server_url + uart_server_url['sn']
    #parse_network_data :  {'ip': '192.168.97.21', 'gateway': '192.168.97.1', 'netmask': '255.255.255.0', 'nameserver': '8.8.8.8', 'sn': 'EK12AQ000003', 'port': '8812'}
    data = json.dumps(uart_server_url)
    print("data: ",data)
    print("data of post_network_data: ",data)
    print("go_server_url: ",go_server_url)
    result = list(range(2))
    result[0]=go_server_url
    result[1]=data
    #res = requests.request(method="POST", url=go_server_url, data=data) #If db doesn't have a value, it won't succeed.

    print("post request success")

    return result



async def post_network_async():

    await post_network_data()
    await process_async()


def main_async():
    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(post_network_async())
    #loop.close()
    asyncio.run(post_network_async())
    #asyncio.run(process_async())

#if __name__ == '__main__':
#    main_async()




'''
device_network_data = await Discover.post_network_data()
await self._session.request("POST", str(device_network_data[0]),data=device_network_data[1])
'''

