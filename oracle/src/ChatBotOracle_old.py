import asyncio
import httpx  # Changed from requests to httpx
import time  # Added for timestamped logs

# Removed ollama import

from .ContractUtility import ContractUtility
from .RoflUtility import RoflUtility


class ChatBotOracle:
    def __init__(self,
                 contract_address: str,
                 network_name: str,
                 openrouter_api_key: str, # Changed from ollama_address
                 rofl_utility: RoflUtility,
                 secret: str):
        contract_utility = ContractUtility(network_name, secret)
        abi, bytecode = ContractUtility.get_contract('ChatBot')

        self.rofl_utility = rofl_utility
        self.openrouter_api_key = openrouter_api_key # Changed assignment
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model_name = "google/gemini-2.0-flash-exp:free" # Default model
        self.contract = contract_utility.w3.eth.contract(address=contract_address, abi=abi)
        self.w3 = contract_utility.w3

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
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Listening for prompts...", flush=True)
        last_processed_block = self.w3.eth.block_number - 1
        
        while True:
            try:
                # Get new events using the correct parameter name 'from_block'
                logs = self.contract.events.PromptSubmitted().get_logs(
                    from_block=last_processed_block + 1
                )
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Found {len(logs)} new events", flush=True)
                
                for log in logs:
                    try:
                        submitter = log.args.sender
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] New prompt submitted by {submitter}", flush=True)
                        
                        prompts = self.retrieve_prompts(submitter)
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Got prompts from {submitter}: {prompts}", flush=True)
                        answers = self.retrieve_answers(submitter)
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Got answers from {submitter}: {answers}", flush=True)
                        
                        if len(answers) > 0 and answers[-1][0] == len(prompts) - 1:  # check promptId
                            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Last prompt already answered, skipping", flush=True)
                            continue
                            
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Asking chat bot", flush=True)
                        answer = self.ask_chat_bot(prompts)
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Got answer: {answer[:50]}{'...' if len(answer) > 50 else ''}", flush=True)
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Storing chat bot answer for {submitter}", flush=True)
                        self.submit_answer(answer, len(prompts) - 1, submitter)
                    except Exception as e:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error processing event: {e}", flush=True)
                
                # Update the last processed block
                current_block = self.w3.eth.block_number
                if current_block > last_processed_block:
                    last_processed_block = current_block
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Updated last processed block to {last_processed_block}", flush=True)
                
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error in log_loop: {e}", flush=True)
                await asyncio.sleep(poll_interval)

    def run(self) -> None:
        self.set_oracle_address()

        # Update asyncio event loop handling for Python 3.12+ compatibility
        try:
            # Try to get the current event loop
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If there is no current event loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(
                asyncio.gather(self.log_loop(2)))
        finally:
            loop.close()

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


    def ask_chat_bot(self, prompts: list[str]) -> str:
        try:
            messages = []
            # Ensure system prompt is first if needed, or structure as required by model
            # For now, just converting user prompts
            for prompt in prompts:
                messages.append({
                    'role': 'user',
                    'content': prompt
                })

            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "HTTP-Referer": "http://localhost", # Replace with your actual site URL if deployed
                "X-Title": "ROFL Chatbot", # Replace with your app name
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model_name,
                "messages": messages
            }

            response = httpx.post(self.openrouter_url, headers=headers, json=payload, timeout=60.0) # Added timeout
            response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

            response_data = response.json()
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                # Assuming the structure follows OpenAI's format
                return response_data["choices"][0]["message"]["content"]
            else:
                print(f"Unexpected response format from OpenRouter: {response_data}")
                return "Error: Unexpected response format"

        except httpx.HTTPStatusError as e:
            print(f"Error calling OpenRouter API (HTTP Status): {e.response.status_code} - {e.response.text}")
            return f"Error: API request failed with status {e.response.status_code}"
        except httpx.RequestError as e:
            print(f"Error calling OpenRouter API (Request Error): {e}")
            return "Error: Could not connect to API"
        except Exception as e:
            print(f"Error processing OpenRouter response: {e}")
            return "Error generating response"

    def submit_answer(self, answer: str, prompt_id: int, address: str):
        # Set a message
        tx_hash = self.contract.functions.submitAnswer(answer, prompt_id, address).transact({'gasPrice': self.w3.eth.gas_price, 'gas': max(3000000, 1500*len(answer))})
        tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"Submitted answer. Transaction hash: {tx_receipt.transactionHash.hex()}")
