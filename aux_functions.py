import os
from os import mkdir
from os import path as ospath

import json
from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException
import httplib2

from ecdsa import SigningKey, SECP256k1
from subprocess import check_output, STDOUT
from pyasn1.codec.der import decoder
from binascii import a2b_hex, b2a_hex
from hashlib import new, sha256
from base58 import b58encode, b58decode
from bitcoin import sign

import Transaction


def hash_160(pk):
    """ Calculates the RIPEMD-160 hash of a given elliptic curve key.

    :param pk: elliptic curve public key (in hexadecimal format).
    :type pk: hex str
    :return: The RIPEMD-160 hash.
    :rtype: bytes
    """

    # Calculate the RIPEMD-160 hash of the given public key.
    md = new('ripemd160')
    h = sha256(a2b_hex(pk)).digest()
    md.update(h)
    h160 = md.digest()

    return h160


def hash_160_to_btc_address(h160, v):
    """ Calculates the Bitcoin address of a given RIPEMD-160 hash from 
    an elliptic curve public key.

    :param h160: RIPEMD-160 hash.
    :type h160: bytes
    :param v: version (prefix) used to calculate the Bitcoin address.

     Possible values:

        - 0x00 for main network (PUBKEY_HASH).
        - 0x6F For testnet (TESTNET_PUBKEY_HASH).
    :type v: int
    :return: The corresponding Bitcoin address.
    :rtype: hex str
    """

    # Add the network version leading the previously calculated RIPEMD-160 hash.
    vh160 = v + h160
    # Double sha256.
    h = sha256(sha256(vh160).digest()).digest()
    # Add the two first bytes of the result as a checksum tailing the RIPEMD-160 hash.
    addr = vh160 + h[0:4]
    # Obtain the Bitcoin address by Base58 encoding the result
    addr = b58encode(addr)

    return addr


def btc_address_to_hash_160(btc_addr):
    """ Calculates the RIPEMD-160 hash from a given Bitcoin address

    :param btc_addr: Bitcoin address.
    :type btc_addr: str
    :return: The corresponding RIPEMD-160 hash.
    :rtype: hex str
    """

    # Base 58 decode the Bitcoin address.
    decoded_addr = b58decode(btc_addr)
    # Covert the address from bytes to hex.
    decoded_addr_hex = b2a_hex(decoded_addr).decode('ascii')
    # Obtain the RIPEMD-160 hash by removing the first and four last bytes of the decoded address, corresponding to
    # the network version and the checksum of the address.
    h160 = decoded_addr_hex[2:-8]

    return h160


def public_key_to_btc_address(pk, v='main'):
    """ Calculates the Bitcoin address of a given elliptic curve public key.

    :param pk: elliptic curve public key.
    :type pk: hex str
    :param v: version used to calculate the Bitcoin address.
    :type v: str
    :return: The corresponding Bitcoin address.

        - main network address if v is 'main.
        - testnet address otherwise
    :rtype: hex str
    """

    PUBKEY_HASH = b"\x00"
    TESTNET_PUBKEY_HASH = b"\x6F"

    # Choose the proper version depending on the provided 'v'.
    if v == 'main':
        v = PUBKEY_HASH
    elif v == 'test':
        v = TESTNET_PUBKEY_HASH
    else:
        raise Exception("Invalid version, use either 'main' or 'test'.")

    # Calculate the RIPEMD-160 hash of the given public key.
    h160 = hash_160(pk)
    # Calculate the Bitcoin address from the chosen network.
    btc_addr = hash_160_to_btc_address(h160, v)

    return btc_addr


def generate_btc_addr(pk, v='main'):
    """ Calculates Bitcoin address associated to a given elliptic curve 
    public key and a given network.

    :param pk: elliptic curve public key (in hexadecimal format).
    :type pk: EC_pub
    :param v: version (prefix) used to calculate the WIF, it depends on 
    the type of network.
    :type v: str
    :return: The Bitcoin address associated to the given public key and 
    network.
    :rtype: str
    """

    # Get the hex representation of the provided EC_pub.
    public_key_hex = get_pub_key_hex(pk)
    # Generate the Bitcoin address of de desired network.
    btc_addr = public_key_to_btc_address(public_key_hex, v)

    return btc_addr


def generate_keys():
    """ Gets a new  elliptic curve key pair using the SECP256K1 elliptic 
    curve (the one used by Bitcoin).

    :return: elliptic curve key pair.
    :rtype: list
    """

    # Generate the key pair from a SECP256K1 elliptic curve.
    sk = SigningKey.generate(curve=SECP256k1)
    pk = sk.get_verifying_key()

    return sk, pk


def get_priv_key_hex(sk_file_path):
    """ Gets the EC private key in hexadecimal format from a key file.

    :param sk_file_path: system path where the EC private key is found.
    :type sk_file_path: str
    :return: private key.
    :rtype: hex str
    """

    # Obtain the private key using an OpenSSL system call.
    cmd = ['openssl', 'ec', '-in', sk_file_path, '-text', '-noout']

    response = check_output(cmd, stderr=STDOUT).decode('ascii')
    # Parse the result to remove all the undesired spacing characters.
    raw_key = response[response.find('priv:') + 8:
                       response.find('pub:')]
    raw_key = raw_key.replace(":", "")
    raw_key = raw_key.replace(" ", "")
    raw_key = raw_key.replace("\n", "")

    # If the key starts with 00, the two first characters are removed.
    if raw_key[:2] == '00':
        sk_hex = raw_key[2:]
    else:
        sk_hex = raw_key

    return sk_hex


def get_pub_key_hex(pk_der):
    """ Converts a public key in hexadecimal format from a DER encoded public key.

    :param pk_der: DER encoded public key
    :type pk_der: bytes
    :return: public key.
    :rtype: hex str
    """

    # Get the asn1 representation of the public key DER data.
    asn1_pk, _ = decoder.decode(pk_der)

    # Get the public key as a BitString. The public key corresponds to the second component
    # of the asn1 public key structure.
    pk_bit = asn1_pk.getComponentByPosition(1)

    # Convert the BitString into a String.
    pk_str = ""
    for i in range(len(pk_bit)):
        pk_str += str(pk_bit[i])

    # Parse the data to get it in the desired form. The hex() deletes the first 0 (0000) and adds '0x'
    pk_hex = '0' + hex(int(pk_str, 2))[2:]
    return pk_hex


def generate_std_scriptpubkey(target_btc_addr):
    OP_DUP = 118
    OP_HASH_160 = 169
    OP_EQUALVERIFY = 136
    OP_CHECKSIG = 172

    h160 = btc_address_to_hash_160(target_btc_addr)

    scriptpubkey = format(OP_DUP, 'x') + format(OP_HASH_160, 'x') + format(int(len(h160) / 2), 'x') + h160 + format(OP_EQUALVERIFY, 'x') + format(OP_CHECKSIG,'x')

    # scriptpubkey = '{:02x}'.format(OP_DUP) +'{:02x}'.format(OP_HASH_160) + '{:02x}'.format(int(len(h160) / 2)) + h160 + '{:02x}'.format(OP_EQUALVERIFY) + '{:02x}'.format(OP_CHECKSIG)
    return scriptpubkey


def build_raw_tx(prev_tx_id, prev_out_index, value, src_btc_addr,
                 dest_btc_addr):
    #assert len(prev_tx_id) == len(prev_out_index) == len(value) == len(src_btc_addr)

    scriptPubKey = []
    for i in range(len(dest_btc_addr)):
        scriptPubKey.append(generate_std_scriptpubkey(dest_btc_addr[i]))

    tx = Transaction.TX()
    tx.build_default_tx(prev_tx_id, prev_out_index, value, scriptPubKey)

    signed_tx = ""
    for i in range(len(src_btc_addr)):
        priv_key = "wallet/" + src_btc_addr[i] + "/sk.pem"
        priv_key_hex = get_priv_key_hex(priv_key)
        signed_tx = sign(tx.hex, 0, priv_key_hex)

    return signed_tx


# def UAB_gen_and_store_keys():
#     #### IMPLEMENTATION GOES HERE ####

#     sk, pk = generate_keys()

#     bAddr = generate_btc_addr(pk.to_der(), 'test')

#     mkdir("wallet/" + bAddr)

#     with open("wallet/" + bAddr + '/pk.pem', 'w') as file:
#         file.write(pk.to_pem())

#     with open("wallet/" + bAddr + '/sk.pem', 'w') as file:
#         file.write(sk.to_pem())


# CUIDADOOO
if __name__ == '__main__':
    # UAB_gen_and_store_keys()
    # UAB_gen_and_store_keys()
    # UAB_gen_and_store_keys()

    print(os.listdir("wallet/"))

    prev_tx_id = ["82f839c581c9d5b2553dab7cd9f1f71c5ec8b258ca6e85307655e902ef7a9a74"]
    # "945c12e7b6f5b26eb857d1bcbbd12892a516eee302917372b1347fbcad4f5198"
    # "9c1d806fa39d5b9ba43b996f73bd397397d1dce47c1f9c542d5fbeef430d00e1"
    prev_out_index = [0]
    value = [110000]
    src_btc_addr = ["mgEVYkAbVgX5Fm9RUSMC2VFa3phDyMXppA"]
    dest_btc_addr = ["mzCNBj4r8BCrh5hwHpFMo5azYw4zqwnJvF"]

    signed_tx = build_raw_tx(prev_tx_id, prev_out_index, value, src_btc_addr, dest_btc_addr)
    print(signed_tx)
    # EXERCISE 4: Broadcast the transaction

    # Set RPC configuration
    rpc_user = "FTI"
    rpc_password = "FTI201819"
    rpc_server = "158.109.79.39"
    rpc_port = 18332

    # Test connection
    rpc_connection = AuthServiceProxy("http://%s:%s@%s:%s" % (rpc_user,
                                                              rpc_password, rpc_server, rpc_port))
    get_info = rpc_connection.getinfo()
    print(get_info)

    # Send transaction

    rpc_connection.sendrawtransaction(signed_tx)


def UAB_get_balance(addr):
    amount = -1

    #### IMPLEMENTATION GOES HERE ####

    h = httplib2.Http()
    (resp_headers, content) = h.request("https://api.blockcypher.com/v1/btc/test3/addrs/" + addr + "/balance", "GET")

    amount = json.JSONDecoder().decode(content)["balance"]

    amount = float(amount) / 10 ^ 8

    ##################################

    return amount
    # Use UAB_get_balance() to compute the balance of some of your addresses

    #### IMPLEMENTATION GOES HERE ####

    print(UAB_get_balance("mzCNBj4r8BCrh5hwHpFMo5azYw4zqwnJvF"))


# EXERCISE 6: Compute total balance of a wallet
#

def UAB_get_total_balance():
    amount = -1
    #### IMPLEMENTATION GOES HERE ####

    amount = 0

    for wallet in os.listdir("wallet/"):
        amount = amount + UAB_get_balance(wallet)

    ##################################

    return amount

    ##################################
# CUIDADDOOOOO
