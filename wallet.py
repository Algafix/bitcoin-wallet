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
from blockcypher import get_address_details
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
    #print(content)
    amount = content['balance']

    return amount


def get_total_balances():
    
    balance_list = []
    total_amount = 0

    for address in os.listdir("wallet/"):
        balance = get_balance(address)
        balance_list.append([address, balance])
        total_amount += balance

    return total_amount, balance_list


def build_raw_tx(prev_tx_id, prev_out_index, value, src_btc_addr,
                 dest_btc_addr):
    #assert len(prev_tx_id) == len(prev_out_index) == len(value) == len(src_btc_addr)

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
        total_balance, address_list = get_total_balances()
        
        print("\nAddresses:")
        for address, balance in address_list:
            print(f"\t{address}: {balance}")

        print('\nTotal balance:\t' + str(total_balance))

    elif "make_transaction" in args:

        _, address_list = get_total_balances()

        print("Addresses:")
        for index, (address, balance) in enumerate(address_list):
            print(f"[{index}] {address}: {balance}")

        # Source Address
        s_addr_index = int(input("From Address...\n"))
        s_addr = address_list[s_addr_index][0]
        s_addr_balance = address_list[s_addr_index][1]

        # Destination Address
        d_addr_index = input("To Address... (Select or write a new address)\n")
        if len(d_addr_index) < 34:
            d_addr = address_list[int(d_addr_index)][0] # 0 is address, 1 is balance
        else:
            d_addr = d_addr_index
        
        # Transaction Value
        tx_value = int(input("The value of...\n"))
        if tx_value == s_addr_balance:
            print(f"You have to pay fees!")
            exit(1)
        elif tx_value > s_addr_balance:
            print(f"You can't transfer more money than the balance of the address!")
            exit(2)
        
        # Transaction Fees and Exchange
        tx_fees = int(input("How many fees you want to pay? (Enter to compute the fees as the difference)\n") or "0")
        if tx_fees == 0:
            exchange = False
            tx_fees = s_addr_balance - tx_value
        else:
            exchange = True
            tx_exchange = s_addr_balance - tx_value - tx_fees
            print(f"Exchange value: {tx_exchange}")
            (exchange_addr,pubk) = new_address()
            print(f"Exchange Address: {exchange_addr}")
        
        # Get UTXOs
        addr_details = get_address_details(s_addr, coin_symbol="btc-testnet", unspent_only=True)
        utxos = addr_details["txrefs"]

        #TODO: Now harcoded to the first UTXO (aka only works if UTXO[0] < tx_value + fees)
        #       Fix by iterating through UTXO's and accumulating balance until having a value
        #       bigger than tx_value + fees (if any). Then idk how to incorporate that to the
        #       build_raw_tx. Maybe prev_tx_hash = [tx1,tx2,...] and prev_tx_output = [tx1_output, tx2_output,...]
        if int(utxos[0]["value"]) < (tx_value + tx_fees):
            print(f"Not yet implemented! Only works if the first UTXO is bigger than value plus fees.")
            print(utxos)
            exit(3)
        else:
            prev_tx_hash = utxos[0]["tx_hash"]
            prev_tx_output = utxos[0]["tx_output_n"]
            new_tx = build_raw_tx([prev_tx_hash], [prev_tx_output], [tx_value, tx_exchange], [s_addr], [d_addr, exchange_addr])
            t = pushtx(tx_hex=new_tx.strip(), coin_symbol="btc-testnet", api_key="c042531962c741879044c11c11b042a2")
            print(f'Transaction ID: {t["t"]["hash"]}')

    elif "try_utxo" in args:
        addr_details = get_address_details("YOUR-ADDRESS-HERE", coin_symbol="btc-testnet", unspent_only=True)
        utxos = addr_details["txrefs"]
        print(utxos)

    elif "try_tx" in args:
        prev_tx_id = ["e1c4c20b1e207121db57d023f0e802fe1bed1fd04c3fb5c5035a53cd0b1c4eb5"]
        prev_out_index = [0]
        value = [100000]
        src_btc_addr = ["mqRPtLdg1REUZnmHtC4jqJUMnxQzqGYVL3"]
        dest_btc_addr = ["mwQA3HJ52C4iioe51wJmgE56DXWkTHEoeM"]

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
