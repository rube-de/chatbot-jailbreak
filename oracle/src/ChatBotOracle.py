import asyncio
import requests
import json
import time 

from .ContractUtility import ContractUtility
from .RoflUtility import RoflUtility


class ChatBotOracle:
    def __init__(self,
                 contract_address: str,
                 network_name: str,
                 openrouter_api_key: str,
                 rofl_utility: RoflUtility,
                 secret: str):
        contract_utility = ContractUtility(network_name, secret)
        abi, bytecode = ContractUtility.get_contract('ChatBotGasless')

        self.rofl_utility = rofl_utility
        self.openrouter_api_key = openrouter_api_key
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model_name = "google/gemini-2.0-flash-exp:free" # Default model
        self.contract = contract_utility.w3.eth.contract(address=contract_address, abi=abi)
        self.w3 = contract_utility.w3
        self.debug_mode = network_name == 'sapphire-localnet'
        if self.debug_mode:
            print(f"Debug mode enabled. Using contract {contract_address} on {network_name}.")

    def set_oracle_address(self):
        contract_addr = self.contract.functions.oracle().call()
        if  contract_addr != self.w3.eth.default_account:
            print(f"Contract oracle {contract_addr} does not match our address {self.w3.eth.default_account}, updating...",)
            tx_params = self.contract.functions.setOracle(self.w3.eth.default_account).build_transaction({'gasPrice': self.w3.eth.gas_price})
            tx_hash = self.rofl_utility.submit_tx(tx_params)
            print(f"Got receipt {tx_hash} {dir(tx_hash)}")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"Updated. Transaction hash: {tx_receipt.transactionHash.hex()}")
        else:
            print(f"Contract oracle {contract_addr} matches our address {self.w3.eth.default_account}")

    async def log_loop(self, poll_interval):
        print(f"Listening for prompts...", flush=True)
        while True:
            logs = self.contract.events.PromptSubmitted().get_logs(from_block=self.w3.eth.block_number)
            for log in logs:
                submitter = log.args.sender
                print(f"New prompt submitted by {submitter}")
                prompts = self.retrieve_prompts(submitter)
                print(f"Got prompts from {submitter}")
                answers = self.retrieve_answers(submitter)
                print(f"Got answers from {submitter}")
                if len(answers)>0 and answers[-1][0] == len(prompts)-1: # check promptId
                    print(f"Last prompt already answered, skipping")
                    break
                print(f"Asking chat bot", flush=True)
                answer = self.ask_chat_bot(prompts, answers)
                print(f"Storing chat bot answer for {submitter}", flush=True)
                self.submit_answer(answer, len(prompts)-1, submitter)
            await asyncio.sleep(poll_interval)

    def run(self) -> None:
        self.set_oracle_address()

        # Run the asynchronous log loop
        try:
            asyncio.run(self.log_loop(2))
        except KeyboardInterrupt:
            print("Oracle stopped.")
        # No need for manual loop closing, asyncio.run handles it.

    def retrieve_prompts(self,
                         address: str) -> list[str]:
        try:
            prompts = self.contract.functions.getPrompts(b'', address).call()
            return prompts
        except Exception as e:
            print(f"Error retrieving prompts: {e}")
            return []

    def retrieve_answers(self,
                         address: str) -> list[(int, str)]:
        try:
            answers = self.contract.functions.getAnswers(b'', address).call()
            return answers
        except Exception as e:
            print(f"Error retrieving answers: {e}")
            return []


    def ask_chat_bot(self, prompts: list[str], answers: list[(int, str)]) -> str:
        try:
            # Retrieve the system prompt from the contract
            system_prompt_text = ""
            try:
                print("Attempting to retrieve system prompt...") # New log
                system_prompt_text = self.contract.functions.getSystemPrompt().call()
                if self.debug_mode and system_prompt_text:
                    print(f"Retrieved system prompt: '{system_prompt_text}'")
                elif self.debug_mode and not system_prompt_text: # New conditional log
                    print("System prompt was retrieved, but it is empty.") # New log
            except Exception as e:
                print(f"Error retrieving system prompt: {e}. Proceeding without it.")

            messages = []
            if system_prompt_text:
                messages.append({
                    'role': 'system',
                    'content': system_prompt_text
                })

            # Create a dictionary for quick lookup of answers by prompt_id
            answer_map = {prompt_id: answer_content for prompt_id, answer_content in answers}

            # Interleave prompts and answers
            for i, prompt in enumerate(prompts):
                messages.append({
                    'role': 'user',
                    'content': prompt
                })
                # Check if there is a corresponding answer for this prompt_id
                if i in answer_map:
                    messages.append({
                        'role': 'assistant',
                        'content': answer_map[i]
                    })

            if self.debug_mode:
                print("Messages sent to OR:")
                print(json.dumps(messages, indent=2))

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "HTTP-Referer": "openrouter_url", 
                "X-Title": "ROFL Chatbot", # TODO: Replace with your app name
                "Content-Type": "application/json"
            }
            payload = {"model": self.model_name, "messages": messages}

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending request to OpenRouter ({len(messages)} messages)...", flush=True)
            response = requests.post(self.openrouter_url, headers=headers, json=payload)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received response from OpenRouter. Status: {response.status_code}", flush=True)

            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses

            response_data = response.json()
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message", {})
                content = message.get("content")
                if content:
                     # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully extracted answer from OpenRouter.", flush=True) # Less verbose
                     return content


            # This part is only reached if client.chat() succeeds
            if self.debug_mode:
                print("Response from OR (message content):")
                # Safely log the message content, or the whole message if it's a dict
                if 'message' in response and isinstance(response['message'], dict) and 'content' in response['message']:
                    print(response['message']['content'])
                elif 'message' in response: # if message is not a dict but has content
                     print(str(response['message'])) # fallback to string representation
                else:
                    print("Ollama response structure not as expected for logging.")

            return response['message']['content']
        except Exception as e_generic: # Generic error
            print(f"Error calling Ollama API (generic exception): {e_generic}")
            # Attempt to see if the generic exception object has more details
            if hasattr(e_generic, 'args') and e_generic.args:
                print(f"  Exception args: {e_generic.args}")
            return "Error generating response (generic exception)"

    def submit_answer(self, answer: str, prompt_id: int, address: str):
        # Set a message
        tx_hash = self.contract.functions.submitAnswer(answer, prompt_id, address).transact({'gasPrice': self.w3.eth.gas_price, 'gas': max(3000000, 1500*len(answer))})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Submitted answer. Transaction hash: {tx_receipt.transactionHash.hex()}")