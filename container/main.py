import json
import getpass
import os
import re
import sys
from pprint import pprint
from datetime import datetime, timezone
import urllib3
import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ENV_PATH = "/usr/src/app/secrets"
VAR_DEBUG = False

# new_state off|auto 
NEW_STATE = sys.argv[1]
if NEW_STATE not in ["off", "auto"]:
    sys.exit(f"Invalid state: {NEW_STATE}, must be 'off' or 'auto'")
    
# settings dict
if os.path.isfile(f"/usr/src/app/settings.json"):
    with open("/usr/src/app/settings.json", "r", encoding="utf-8") as fr:
        SETTINGS_DICT=json.load(fr)
elif os.path.isfile(f"settings.json"):
    with open(f"settings.json", "r", encoding="utf-8") as fr:
        SETTINGS_DICT=json.load(fr)
else:
    sys.exit(f"settings not found: {os.listdir()}")

# api password
if os.path.isfile(f"{ENV_PATH}/controller_api_password"):
    with open(f"{ENV_PATH}/controller_api_password", "r", encoding="utf-8") as fr:
        PASSWORD=fr.read()
else:
    while True:
        PASSWORD=getpass.getpass("Controller Password unifi_admin:  or e for sys.exit: ")
        if len(PASSWORD) > 10:
            break 
        elif PASSWORD == "e":
            sys.exit("Exit from user")

# Set Variables from settings file
USER = SETTINGS_DICT['controller_api_user']
GATEWAY_IP = SETTINGS_DICT['controller_ip']
GATEWAY_PORT =SETTINGS_DICT['controller_api_port'] 
AUTHURL = SETTINGS_DICT['controller_auth_url']
SWITCH_MAC = SETTINGS_DICT['switch_mac']
PORT_LIST = SETTINGS_DICT['ports']

def custom_print(msg, print_type="p") -> None:
    if VAR_DEBUG is True:
        if print_type == "pp":
            pprint(msg)
        else:
            print(msg)

def connect_to_controller():
    """ Request"""
    headers = {"Accept": "application/json","Content-Type": "application/json"}
    url = f"https://{GATEWAY_IP}:{GATEWAY_PORT}/{AUTHURL}"
    auth = {"username": USER,"password": PASSWORD}
    session = requests.Session()
    response = session.post(url,headers=headers,data=json.dumps(auth), verify=False)
    print (response)
    if response.status_code!=200:
        sys.exit(f"unable_to_connect: Status_Code: {response.status_code}")
    cookiestring=response.headers["Set-Cookie"]
    tokenobject=re.search("csrf_token=[0-9a-zA-Z]*", cookiestring)
    token=tokenobject[0].split('=')[1]
    tokenheaders = {'Authorization': f"Bearer {token}"}
    return(session, tokenheaders)

def get_device_dict_details(session, headers, mac) -> dict:
    """
    query controller for device infos   28:70:4e:c0:53:bb
    """
    request_url=f"https://{GATEWAY_IP}:{GATEWAY_PORT}/api/s/default/stat/device/{mac}"
    api_response=session.get(request_url, headers=headers, verify=False)
    return api_response.json()


def change_poe_on_port(session, headers, mac, port_list: list, new_state: str, device_data):
    """
    disable poe on port states: auto|off
    https://community.home-assistant.io/t/solved-unifi-allow-poe-switching-of-connected-unifi-devices/230358/3
    Example: "28:70:4e:c0:53:bb", ["2","3"], off|auto
    """
    switch_id = device_data['data'][0]['_id']
    request_url=f"https://{GATEWAY_IP}:{GATEWAY_PORT}/api/s/default/rest/device/{switch_id}"
    port_overrides = device_data['data'][0]['port_overrides']
    # Update the port_overrides config with new settings
    for value in port_overrides:
        custom_print(value, "pp")
        custom_print(f""" - value {value.get('port_idx')}, current_mode: {value.get('poe_mode')}
         - port_list: {port_list} """)
        if value['port_idx'] in port_list:
            value['poe_mode'] = new_state
            print(f"POE mode for {mac} port {value['port_idx']} set to {new_state}")
    #return port_overrides
    data =  { 'port_overrides': port_overrides }
    api_response=session.put(request_url, headers=headers, data=json.dumps(data), verify=False)
    if api_response.status_code == 200:
        custom_print(f"POE changed on {mac} ports: {port_list} to new state: {new_state}")

    else:
        custom_print(f"""Failed to change POE on {mac} ports: {port_list},
         {api_response.text}, Code: {api_response.status_code}""")
    custom_print(api_response.text)

def change_poe_status_on_ports(mac: str, ports: list, status: str):
    """ 
    disable poe for ap 1, use mac in query and _id for settings
    Example: "28:70:4e:c0:53:bb", ["2","3"], off|auto
    """
    session,tokenheaders=connect_to_controller()
    device_data=get_device_dict_details(session, tokenheaders, mac)
    custom_print("- - - start config job --- "* 5)
    change_poe_on_port(session, tokenheaders, mac, ports, status, device_data)

if __name__ == "__main__":
    change_poe_status_on_ports(SWITCH_MAC, PORT_LIST, NEW_STATE)
