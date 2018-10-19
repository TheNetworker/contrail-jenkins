#!/usr/bin/python

__author__ = "Bassim Aly"
__EMAIL__ = "basim.alyy@gmail.com"


import requests
from pprint import pprint
import sseclient
import json

contrail_analytics_address = "192.168.4.16"
contrail_controller_address = "192.168.4.18"
openstack_keystone_address = "https://xx.xx.xx.xx:13000/v2.0/tokens"
openstack_username = "admin"
openstack_password = "xxxxxxxxx"
headers = {"Content-type": "application/json"}
data = {"auth":{"tenantName": "admin", "passwordCredentials":{"username": openstack_username, "password":openstack_password}}}

access_token_response = requests.post(openstack_keystone_address, headers=headers, data=json.dumps(data))

token = access_token_response.json()["access"]["token"]["id"]

print (" ** Obtained token from openstack: {0} ** ".format(token))

contrail_headers = {'content-type': 'application/json',
           'X-Auth-Token': token,
           'Cache-Control': "no-cache"
           }

def with_requests(url):
    return requests.get(url, stream=True)


def extract_data_from_response(network_response,event):
    uuid = network_response['uuid']
    contrail_controller_address = "192.168.4.18"
    contrail_url = 'http://{0}:8082/virtual-network/{1}'.format(contrail_controller_address, uuid)
    contrail_response = requests.request('GET', contrail_url, headers=contrail_headers).json()

    display_name = contrail_response['virtual-network']['display_name']

    try:
        ipam_info = contrail_response['virtual-network']['network_ipam_refs'][0]['attr']['ipam_subnets'][0]

        default_gateway = ipam_info['default_gateway']
        network_address = ipam_info['subnet']['ip_prefix']

        network_mask = ipam_info['subnet']['ip_prefix_len']

        # physical_router = network_response['virtual-network']['physical_router_back_refs']
        physical_router_mgmt_ip = json.loads(event.data)['value']['elements']['physical_router_management_ip']

        physical_router_username = json.loads(event.data)['value']['elements']['physical_router_user_credentials'][
            'username']
        physical_router_password = json.loads(event.data)['value']['elements']['physical_router_user_credentials'][
            'password']
    except:
        pass

    return uuid,display_name,default_gateway,network_address,network_mask,physical_router_mgmt_ip

url = 'http://{0}:8081/analytics/uve-stream?cfilt=ContrailConfig'.format(contrail_analytics_address)

stream_channel = with_requests(url)

client = sseclient.SSEClient(stream_channel)
current_extended_networks = []
networks_diff = []
for event in client.events():

    try:
        if u"bgp_router_refs" in json.loads(event.data)['value']['elements']:
            print("** Change in BGP router detected **")

            if json.loads(event.data)['value']['elements']['virtual_network_refs'] not in current_extended_networks:
                new_extended_networks = json.loads(event.data)['value']['elements']['virtual_network_refs']
                new_extended_networks = json.loads(new_extended_networks)
                print type(new_extended_networks)

            if current_extended_networks != new_extended_networks:
                print("** Networks change occur, Need to check if push or withdraw happen **")

                for network_record in new_extended_networks:
                    if network_record not in current_extended_networks:
                        networks_diff.append(network_record)

                if networks_diff:
                    print("** New Networks after filtering are: **")
                    print(networks_diff)

                    for network_response in networks_diff:
                        print extract_data_from_response(network_response,event)

                else:
                    print("** Networks are withdrawn from the SDN Gateway **")


                    print("="*80)

                    # TODO: execute jenkins workflow here

            current_extended_networks = new_extended_networks
            print("** Clearing new extended networks **")
            new_extended_networks = []
            networks_diff = []
    except Exception as e:
        print(e)
        pass
