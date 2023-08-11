"""
CrazyToolBox, a web3 utilities GUI toolbox.
© 2023 Telefónica Digital España S.L.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.
 
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from decimal import Decimal, Context, ROUND_HALF_DOWN, setcontext, BasicContext

from eth_account.messages import encode_defunct
from ratelimit import limits, sleep_and_retry
from eth_abi import decode
from web3 import Web3
import requests

from src.custom_types import SOLIDITY_DATA_TYPES


class ToolBoxCore:
    def __init__(self, signal):
        self.__signal = signal

    # 5 requests per 2 second because of the API limits
    @sleep_and_retry
    @limits(calls=5, period=2)
    def resolve_function_selector(self, func_selector: str):
        response = requests.get(f"https://www.4byte.directory/api/v1/signatures/?hex_signature={func_selector}")
        if response.status_code != 200 or response.json()["results"] == []:
            return ["Not found"]
        else:
            return [result["text_signature"] for result in response.json()["results"]]

    def wei_converter(self, value: str, currencyFrom: str, currencyTo: str):
        try:
            value = float(value)

            # Set the precision to 30 decimal places
            wei_converter_context = Context(prec=30, rounding=ROUND_HALF_DOWN)
            setcontext(wei_converter_context)

            wei = Decimal(Web3.to_wei(value, currencyFrom))
            output = "{:.30f}".format(Decimal(Web3.from_wei(wei, currencyTo))).rstrip("0")

            # If the output is an integer, remove the decimal point
            if output[-1] == ".":
                output = output[:-1]

            self.__signal.result_to_copy.emit(output)
            self.__signal.result.emit(f"**{output}** {currencyTo}")

            # Reset the precision to the original value
            setcontext(BasicContext)
        except:
            self.__signal.result_to_copy.emit("")
            if value == "":
                self.__signal.result.emit("Enter a value")
            else:
                self.__signal.result.emit(f"Invalid value: **{value}**")

    def function_selector_encoder(self, func_name: str, params_type: list[str]):
        func_name = func_name.strip()

        for param in params_type:
            if param not in SOLIDITY_DATA_TYPES:
                return

        if func_name == "":
            self.__signal.function_signature.emit("")
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("")
            return

        # https://docs.soliditylang.org/en/v0.8.6/grammar.html#identifiers
        for char in func_name:
            if char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$_":
                self.__signal.function_signature.emit("")
                self.__signal.result_to_copy.emit("")
                self.__signal.result.emit("Invalid function name")
                return

        if func_name[0] in "0123456789":
            self.__signal.function_signature.emit("")
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Invalid function name")
            return

        self.__signal.function_signature.emit(f'{func_name}({",".join(params_type)})')
        output = Web3.keccak(text=f'{func_name}({",".join(params_type)})')[:4].hex()

        self.__signal.result_to_copy.emit(output)
        self.__signal.result.emit(f"Your function selector is: **{output}**")

    def function_selector_encoder_advanced(self, func_signature: str):
        func_signature = func_signature.strip().replace(" ", "")

        if func_signature == "":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("")
            return

        try:
            func_name = func_signature.split("(")[0]
            params_type = func_signature.split("(")[1].split(")")[0].split(",")
        except:
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Invalid function signature")
            return

        for param in params_type:
            if param not in SOLIDITY_DATA_TYPES:
                self.__signal.result_to_copy.emit("")
                self.__signal.result.emit("Invalid function signature")
                return

        # https://docs.soliditylang.org/en/v0.8.6/grammar.html#identifiers
        if func_name[0] in "0123456789":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Invalid function name")
            return

        for char in func_name:
            if char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789$_":
                self.__signal.result_to_copy.emit("")
                self.__signal.result.emit("Invalid function name")
                return

        output = Web3.keccak(text=func_signature)[:4].hex()
        self.__signal.result_to_copy.emit(output)
        self.__signal.result.emit(f"Your function selector is: **{output}**")

    def function_selector_decoder(self, func_selector: str):
        func_selector = func_selector.strip().replace("0x", "")

        if func_selector == "":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("")
            return

        if len(func_selector) != 8:
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Invalid function selector")
            return

        for char in func_selector:
            if char not in "0123456789abcdef":
                self.__signal.result_to_copy.emit("")
                self.__signal.result.emit("Invalid function selector, only hex characters")
                return

        decode = self.resolve_function_selector(func_selector)
        if decode[0] == "Not found":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Function signature not found in 4byte.directory")
        else:
            self.__signal.result_to_copy.emit(", ".join(decode))
            if len(decode) > 1:
                self.__signal.result.emit(f"Multiple function signatures found:<br />**{'<br />'.join(decode)}**")
            else:
                self.__signal.result.emit(f"Your function signature is: **{', '.join(decode)}**")

    def decode_transaction_input(self, transaction_input: str):
        transaction_input = transaction_input.replace("0x", "")

        # Contract creation
        if transaction_input[:8] == "60806040":
            tx_type = "Contract creation"
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Transaction type: **Contract creation**<br />Checking for function selectors in the bytecode...")

            function_selectors = transaction_input.split("8063")[1:]
            function_selectors_dict = {}
            for function_selector in function_selectors:
                if function_selector != "":
                    encoded = "0x" + function_selector[:8]
                    decoded = self.resolve_function_selector(encoded)
                    function_selectors_dict[encoded] = decoded

            output = "Transaction type: **Contract creation**<br />Function selectors found in the bytecode:<br />{}".format(
                "<br />".join(
                    [
                        f"__{key}{' [!]' if len(value) > 1 else ''}__:<br /> - **{'<br /> - '.join(value)}**"
                        for key, value in function_selectors_dict.items()
                    ]
                )
            )
            self.__signal.result_to_copy.emit(output)
            self.__signal.result.emit(output)

        # Contract call
        else:
            tx_type = self.resolve_function_selector(transaction_input[:8])

            if tx_type[0] != "Not found" and len(transaction_input) > 8:
                output = ""
                for type in tx_type:
                    try:
                        tx_params_body = transaction_input[8:]
                        tx_params_type = type.split("(")[1].split(")")[0].split(",")
                        result = decode(tx_params_type, bytes.fromhex(tx_params_body))
                        tx_params_list = ["- " + tx_params_type[i] + ": " + str(result[i]) for i in range(len(tx_params_type))]

                        if output != "":
                            output += "<br />"

                        output += "Transaction type: **<br /> - {}**<br />Transaction params (values):<br />**{}**".format(
                            type, ",<br />".join(tx_params_list)
                        )
                    except:
                        output += "Transaction type: **<br /> - {}**<br />Invalid transaction params".format(type)

                self.__signal.result_to_copy.emit(output)
                self.__signal.result.emit(output)
            else:
                self.__signal.result_to_copy.emit("")
                self.__signal.result.emit(
                    "Transaction type: **<br /> - {}**<br />No transaction params found".format("<br /> - ".join(tx_type))
                )

    def keccak256_hash(self, value: str):
        if value == "":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("")
            return
        else:
            output = Web3.keccak(text=value).hex()
            self.__signal.result_to_copy.emit(output)
            self.__signal.result.emit(f"Your hash is: **{output}**")

    def eip55_validator(self, address: str):
        if address == "":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("")
            return

        tempOutput = ""
        valid_address = ""
        if Web3.is_address(address):
            tempOutput += "✓ Valid address<br />"
            if Web3.is_checksum_address(address):
                tempOutput += "✓ Valid checksum address"
            else:
                tempOutput += "✕ Invalid checksum address"
                valid_address = Web3.to_checksum_address(address)
                tempOutput += "<br />✓ Valid checksum address: **{}**".format(valid_address)
        else:
            tempOutput += "✕ Invalid address"

        self.__signal.result_to_copy.emit(valid_address)
        self.__signal.result.emit(tempOutput)

    def get_signer_owner(self, signature_message_or_hash: str, signature: str):
        if signature_message_or_hash == "" or signature == "":
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("")
            return

        try:
            if signature_message_or_hash[:2] == "0x":
                signature_message_or_hash = encode_defunct(hexstr=signature_message_or_hash)
            else:
                signature_message_or_hash = encode_defunct(text=signature_message_or_hash)
        except:
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Invalid signature message or hash")
            return

        try:
            output = Web3.to_checksum_address(Web3().eth.account.recover_message(signature_message_or_hash, signature=signature))
            self.__signal.result_to_copy.emit(output)
            self.__signal.result.emit(f"Signature owner: **{output}**")
        except:
            self.__signal.result_to_copy.emit("")
            self.__signal.result.emit("Invalid signature")
