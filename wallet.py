import json
import os
from os import path as ospath
from pathlib import Path

import sys

import requests

import Transaction
from Transaction import TX
import aux_functions as aux
from blockcypher import pushtx
from blockcypher import simple_spend
from blockcypher import get_blockchain_overview
import blockcypher


def new_address():
    sk, pk = aux.generate_keys()

    bAddr = aux.generate_btc_addr(pk.to_der(), 'test').decode()

    Path("wallet").mkdir(exist_ok=True)
    Path("wallet/" + bAddr).mkdir(exist_ok=False)

    with open("wallet/" + bAddr + '/pk.pem', 'w') as file:
        file.write(pk.to_pem().decode())

    with open("wallet/" + bAddr + '/sk.pem', 'w') as file:
        file.write(sk.to_pem().decode())

    return bAddr, aux.get_pub_key_hex(pk.to_der())


def get_balance(addr):
    url = "https://api.blockcypher.com/v1/btc/test3/addrs/" + addr + "/balance"
    request = requests.get(url)
    content = request.json()
    print(content)
    amount = content['balance']
    amount = float(amount / (10 ** 8))

    return amount


def get_total_balance():
    amount = 0

    for wallet in os.listdir("wallet/"):
        amount = amount + get_balance(wallet)

    return amount


def build_raw_tx(prev_tx_id, prev_out_index, value, src_btc_addr,
                 dest_btc_addr):
    assert len(prev_tx_id) == len(prev_out_index) == len(value) == len(src_btc_addr)

    scriptPubKey = []
    for i in range(len(dest_btc_addr)):
        scriptPubKey.append(aux.generate_std_scriptpubkey(dest_btc_addr[i]))

    tx = Transaction.TX()
    tx.build_default_tx(prev_tx_id, prev_out_index, value, scriptPubKey)

    signed_tx = ""
    for i in range(len(src_btc_addr)):
        priv_key = "wallet/" + src_btc_addr[i] + "/sk.pem"
        priv_key_hex = aux.get_priv_key_hex(priv_key)
        signed_tx = aux.sign(tx.hex, 0, priv_key_hex)

    return signed_tx


if __name__ == "__main__":

    opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

    if "--help" in opts:
        print("new_address: Creates a new Bitcoin address.")
        print("info: Shows the current addresses and pubkeys.")

    elif "new_address" in args:
        (addr, pubk) = new_address()
        print("\n-----------------------------")
        print("Created Bitcoin address: \n" + addr + "\n")
        print("With the public key: \n" + pubk)
        print("-----------------------------\n")
    elif "get_balance" in args:
        print(get_total_balance())
    elif "try_tx" in args:
        prev_tx_id = ["a42eef2be826bac6b2ccdfb664da3df45843dd79726ee10dc74e3444d13f878f"]
        # "945c12e7b6f5b26eb857d1bcbbd12892a516eee302917372b1347fbcad4f5198"
        # "9c1d806fa39d5b9ba43b996f73bd397397d1dce47c1f9c542d5fbeef430d00e1"
        prev_out_index = [0]
        value = [100]
        src_btc_addr = ["mx2Hw3o1k45aKSquTGd8jcPqr2mCWwWcj7"]
        dest_btc_addr = ["mjzmGEUbigJSuuGKB1YFotXs5KqLKKgP9A"]

        signed_tx = build_raw_tx(prev_tx_id, prev_out_index, value, src_btc_addr, dest_btc_addr)
        print(signed_tx.strip())
        t = pushtx(tx_hex=signed_tx.strip(), coin_symbol="btc-testnet", api_key="c042531962c741879044c11c11b042a2")
        print(t)

        #priv_key = "wallet/mjzmGEUbigJSuuGKB1YFotXs5KqLKKgP9A/sk.pem"
        #priv_key_hex = aux.get_priv_key_hex(priv_key)
        #simple_spend(from_privkey=priv_key_hex, to_address='mx2Hw3o1k45aKSquTGd8jcPqr2mCWwWcj7', to_satoshis=100000, api_key="c042531962c741879044c11c11b042a2")
        #print(t)

    else:
        raise SystemExit(f"Not a valid option or argument. Use --help.")
