import os
from os import path as ospath
from pathlib import Path

import sys
from Transaction import TX
import aux_functions as aux

def init():

    sk, pk = aux.generate_keys()

    bAddr = aux.generate_btc_addr(pk.to_der(), 'test').decode()

    Path("wallet").mkdir(exist_ok=True)
    Path("wallet/"+bAddr).mkdir(exist_ok=False)

    with open("wallet/" + bAddr + '/pk.pem', 'w') as file:
        file.write(pk.to_pem().decode())

    with open("wallet/" + bAddr + '/sk.pem', 'w') as file:
        file.write(sk.to_pem().decode())
    
    return (bAddr, aux.get_pub_key_hex(pk.to_der()))

if __name__ == "__main__":

    opts = [opt for opt in sys.argv[1:] if opt.startswith("-")]
    args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]

    if "--help" in opts:
        print("init: Generates a new wallet and a new Bitcoin address.")
        print("new_address: Creates a new Bitcoin address.")
        print("info: Shows the current addresses and pubkeys.")

    elif "init" in args:
        (addr,pubk) = init()
        print("\n-----------------------------")
        print("Created Bitcoin address: " + addr)
        print("With the public key: " + pubk)
        print("-----------------------------\n")
    else:
        raise SystemExit(f"Not a valid option or argument. Use --help.")