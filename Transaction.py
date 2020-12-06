def change_endianness(x):
    # If there is an odd number of elements, we make it even by adding a 0
    if (len(x) % 2) == 1:
        x += "0"
    #y = x.decode('hex')
    y = bytes.fromhex(x)
    z = y[::-1]

    return z.hex()


def decode_varint(varint):
    if len(varint) > 2:
        decoded_varint = int(change_endianness(varint[2:]), 16)
    else:
        decoded_varint = int(varint, 16)

    return decoded_varint


def int2bytes(a, b):
    a= int(a)
    b= int(b)
    return ('%0' + str(2 * b) + 'x') % a


class TX:

    def __init__(self, version=None, inputs=None, prev_tx_id=None,
                 prev_out_index=None, scriptSig_len=None, scriptSig=None,
                 nSequence=None, outputs=None, value=None,
                 scriptPubKey_len=None, scriptPubKey=None, nLockTime=None):
        if prev_tx_id is None:
            prev_tx_id = []
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.nLockTime = nLockTime

        if prev_tx_id is None:
            self.prev_tx_id = []
        else:
            self.prev_tx_id = prev_tx_id

        if prev_out_index is None:
            self.prev_out_index = []
        else:
            self.prev_out_index = prev_out_index

        if scriptSig is None:
            self.scriptSig = []
        else:
            self.scriptSig = scriptSig

        if scriptSig_len is None:
            self.scriptSig_len = []
        else:
            self.scriptSig_len = scriptSig_len

        if nSequence is None:
            self.nSequence = []
        else:
            self.nSequence = nSequence

        if value is None:
            self.value = []
        else:
            self.value = value

        if scriptPubKey is None:
            self.scriptPubKey = []
        else:
            self.scriptPubKey = scriptPubKey

        if scriptPubKey_len is None:
            self.scriptPubKey_len = []
        else:
            self.scriptPubKey_len = scriptPubKey_len

        self.hex = None
        self.offset = 0

    def to_hex(self):
        if self.hex is None:
            self.hex = self.version + self.inputs

        for i in range(len(self.prev_tx_id)):
            self.hex += self.prev_tx_id[i] + self.prev_out_index[i] + self.scriptSig_len[i] \
                        + self.scriptSig[i] + self.nSequence[i]

        self.hex += self.outputs

        for i in range(len(self.scriptPubKey)):
            self.hex += self.value[i] + self.scriptPubKey_len[i] + self.scriptPubKey[i]

        self.hex += self.nLockTime

        return self.hex

    def build_default_tx(self, prev_tx_id, prev_out_index, value,
                         scriptPubKey, scriptSig=None):

        self.version = "01000000"

        n_inputs = len(prev_tx_id)
        self.inputs = int2bytes(n_inputs, 1)

        for i in range(n_inputs):
            self.prev_tx_id.append(change_endianness(prev_tx_id[i]))

        self.prev_out_index.append(change_endianness(int2bytes(prev_out_index[i], 4)))

        for i in range(n_inputs):
            if scriptSig is None:
                self.scriptSig.append("0")
                self.scriptSig_len.append("0")
            else:
                self.scriptSig_len.append(int2bytes(len(scriptSig[i]) / 2, 1))
            self.nSequence.append("ffffffff")

        n_outputs = len(scriptPubKey)
        print(n_outputs)
        self.outputs = int2bytes(n_outputs, 1)
        print(self.outputs)
        print(n_outputs.to_bytes(1,'big'))

        for i in range(n_outputs):
            print(value[i])
            #self.value.append(change_endianness(value[i].to_))
            self.value.append(change_endianness(int2bytes(value[i], 8)))

            self.scriptPubKey_len.append(int2bytes(len(scriptPubKey[i]) / 2, 1))
            self.scriptPubKey = scriptPubKey

        self.nLockTime = "00000000"
        self.to_hex()
