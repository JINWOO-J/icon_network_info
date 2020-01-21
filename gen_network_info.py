#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from lib.utils import *

network_info = [
    {
        "network_name": "mainnet",
        "network_alias": "mainnet",
        "nid": "0x1",
        "channel": "icon_dex",
        "crep_root_hash": "0xd421ad83f81a31abd7f6813bb6a3b92fa547bdb6d5abc98d2d0852c1a97bcca5",
        "api_endpoint": "https://ctz.solidwallet.io",
        "tracker": "https://tracker.solidwallet.io",
        "transaction_fee": "on",
        "score_audit": "on",
        "switch_bh_versions": {
            "0.1a": 0,
            "0.3": 10324749,
            "0.4": 12640761,
            "0.5": 14473622
        },
        "description": "MainNet"
    },
    {
        "network_name": "testnet",
        "network_alias": "Euljiro",
        "nid": "0x2",
        "channel": "icon_dex",
        "crep_root_hash": "0x38ec404f0d0d90a9a8586eccf89e3e78de0d3c7580063b20823308e7f722cd12",
        "api_endpoint": "https://test-ctz.solidwallet.io",
        "tracker": "https://trackerdev.icon.foundation",
        "transaction_fee": "on",
        "score_audit": "on",
        "switch_bh_versions": {
            "0.1a": 0,
            "0.3": 1,
            "0.4": 10,
            "0.5": 524360
        },
        "description": "Testnet for Exchanges"
    },
    {
        "network_name": "bicon",
        "network_alias": "Yeouido",
        "nid": "0x3",
        "channel": "icon_dex",
        "crep_root_hash": "0xde237a62f194477289711818a75c3040f887b5854ea20683a7cde0947c20e436",
        "api_endpoint": "https://bicon.net.solidwallet.io",
        "tracker": "https://bicon.tracker.solidwallet.io",
        "transaction_fee": "on",
        "score_audit": "off",
        "switch_bh_versions": {
            "0.1a": 0,
            "0.3": 8328000,
            "0.4": 8328100,
            "0.5": 8882950
        },
        "description": "Testnet for DApps"
    },
    {
        "network_name": "zicon",
        "network_alias": "Pagoda",
        "nid": "0x50",
        "channel": "icon_dex",
        "crep_root_hash": "0x9718f5d6d6ddb77f547ecc7113c8f1bad1bf46220512fbde356eee74a90ba47c",
        "api_endpoint": "https://zicon.net.solidwallet.io",
        "tracker": "https://zicon.tracker.solidwallet.io",
        "transaction_fee": "on",
        "score_audit": "off",
        "switch_bh_versions": {
            "0.1a": 0,
            "0.3": 1,
            "0.4": 1587271,
            "0.5": 3077345
        },
        "description": "TestNet for PReps"
    },
]


if __name__ == '__main__':
    md5_checksum_list = []
    all_network_info = []
    changed_list = []
    # output_path = f"{os.getcwd()}/conf"
    output_path = "conf"
    cloudfront_domain = "networkinfo.solidwallet.io"
    download_url_prefix = f"https://{cloudfront_domain}/{output_path}"
    updated_time = todaydate("log")
    for network in network_info:
        network['updated_time'] = updated_time
        network_now = network
        network_name = network.get("network_name")
        output_filename = f"{output_path}/{network_name}.json"

        network_prev = openJson(output_filename)
        added, removed, modified, same = dict_compare(network, network_prev)
        if added or removed or modified:
            kvPrint(f"Changed network", network_name)
            kvPrint("added element", added, value_check=True)
            kvPrint("removed element", removed, value_check=True)
            kvPrint("modified element", modified, value_check=True)
            writeJson(output_filename, network)
            changed_list.append(output_filename)
            md5hash = get_md5(output_filename)
            md5_checksum_list.append({"filename": f"{download_url_prefix}/{network_name}.json", "md5_checksum": md5hash})
            print("\n")
        else:
            if network_prev:
                network_now = network_prev
        all_network_info.append(network_now)

    if len(md5_checksum_list) > 0:
        writeJson(f"{output_path}/md5_checksum.json", md5_checksum_list)
        writeJson(f"{output_path}/all.json", all_network_info)
        DistributionId = get_DistributionId(cloudfront_domain)
        invalidate_list = [f'{output_path}/md5_checksum.json', f"{output_path}/all.json"] + changed_list
        CPrint("== Upload to S3 ==")
        for file in invalidate_list:
            multi_part_upload_with_s3(filename=file, key_path=file, bucket="networkinfo")
        CPrint("== Invalidate Cloudfront Cache ==")
        invalidate_list = ['/{}'.format(f) for f in invalidate_list]
        invalidate_cloudfont(DistributionId, invalidate_list)
    else:
        print("No change")

    CPrint("== Generate README.md ==")
    readme_header = """
    # ICON Network info
    Describes information about the ICON network.
    """.strip()
    readme_tail = ""
    readme_tail += "Generated on => " + todaydate("log") + "<br><br> \n"

    for network_info in all_network_info:
        network_name = network_info.get("network_name")
        readme_tail += f'# {network_info.get("network_name")} ({network_info.get("network_alias")}) \n'

        output_filename = f"{output_path}/{network_name}.json"
        md5hash = get_md5(output_filename)

        readme_tail += f'###### {download_url_prefix}/{network_name}.json  / md5: ({md5hash}) \n'
        readme_tail += "|key|value| \n"
        readme_tail += "|-----|-----|\n"
        for key, value in network_info.items():
            readme_tail += f"|{key}|{value}|\n"
        # readme_tail += writer.dumps()
    writeFile("README.md", readme_header + "\n" + readme_tail)