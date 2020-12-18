import json
import os
import sys

from os import path as ospath
from pathlib import Path
from mnemonic import Mnemonic
from bip44 import Wallet

import Transaction
from bitcoin import sign

from Transaction import TX
import aux_functions as aux

import blockcypher
from blockcypher import pushtx
from blockcypher import get_address_details
from blockcypher import get_address_overview

from coincurve import PrivateKey, PublicKey



##TODO: THIS IS BIP 44
def prueba():
    if not os.path.exists("words.txt"):
        mnemo = Mnemonic("english")
        words = mnemo.generate(strength=256)

        with open("words.txt", 'w') as f:
            f.write(words)

        print(words)
    else:
        with open("words.txt", 'r') as f:
            words = f.read()
    print(words)
    w = Wallet(words)
    sk, pk = w.derive_account("TESTNET", account=0, address_index=0)
    sk = PrivateKey(sk)
    pk_bytes = bytes.fromhex(pk) if isinstance(pk, str) else pk
    if len(pk_bytes) != 64:
        pk_bytes = PublicKey(pk_bytes).format(False)[1:]
    print(sk.to_der())
    #aux.generate_btc_addr(sk.to_der(),pk, 'test').decode()

############################


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
    #url = "https://api.blockcypher.com/v1/btc/test3/addrs/" + addr + "/balance"

    #request = requests.get(url)
    #content = request.json()
    #print(content)
    #amount = content['balance']
    amount = get_address_overview(addr,coin_symbol="btc-testnet")['balance']


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

    signed_tx = tx.hex
    for i in range(len(prev_tx_id)):
        priv_key = "wallet/" + src_btc_addr + "/sk.pem"
        priv_key_hex = aux.get_priv_key_hex(priv_key)

        signed_tx = sign(signed_tx, i, priv_key_hex)

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
            print(f"\t{address}: {balance} satoshis")

        print(f'\nTotal balance:\t {total_balance} satoshis')

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
        if tx_fees == 0 or (tx_fees + tx_value) == s_addr_balance:
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

        prev_tx_list = []
        prev_tx_output_list = []
        tx_value_list = [tx_value]
        d_addr_list = [d_addr]

        for utxo in utxos:
            prev_tx_list.append(utxo["tx_hash"])
            prev_tx_output_list.append(utxo["tx_output_n"])
        
        if exchange:
            tx_value_list.append(tx_exchange)
            d_addr_list.append(exchange_addr)

        new_tx = build_raw_tx(prev_tx_list, prev_tx_output_list, tx_value_list, s_addr, d_addr_list)
        t = pushtx(tx_hex=new_tx.strip(), coin_symbol="btc-testnet", api_key="c042531962c741879044c11c11b042a2")

        if "error" in t:
            print(t)
        else:
            print(f'Transaction ID:\n{t["tx"]["hash"]}')

    elif "try_utxo" in args:
        addr_details = get_address_details("mqa4rqExcA7GY8ZqGhpXted6UQNJnpGA2B", coin_symbol="btc-testnet", unspent_only=True)
        utxos = addr_details["txrefs"]
        print(utxos)

    else:
        raise SystemExit(f"Not a valid option or argument. Use --help.")
