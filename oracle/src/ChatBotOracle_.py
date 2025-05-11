import asyncio
import httpx
import time
import traceback
import functools
import sys

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ChatBotOracle.py loading...", flush=True)

from .ContractUtility import ContractUtility
from .RoflUtility import RoflUtility # Keep RoflUtility in case needed

class ChatBotOracle:
    """
    Oracle service that listens for prompts on a smart contract,
    queries an external LLM API (OpenRouter), and submits answers back.
    Uses asyncio for non-blocking operations.
    """
    def __init__(self,
                 contract_address: str,
                 network_name: str,
                 openrouter_api_key: str,
                 rofl_utility: RoflUtility, # Keep RoflUtility instance
                 secret: str):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Initializing ChatBotOracle...", flush=True)
        try:
            # Initialize ContractUtility (handles web3 setup)
            self.contract_utility = ContractUtility(network_name, secret)
            self.w3 = self.contract_utility.w3 # Get configured web3 instance
            self.account_address = self.w3.eth.default_account # Get address from wrapped instance

            # Load contract ABI and bytecode
            abi, _ = ContractUtility.get_contract('ChatBotGasless') # Ignore bytecode for now

            # Create contract object
            self.contract = self.w3.eth.contract(address=contract_address, abi=abi)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Contract object created for address: {contract_address}", flush=True)

            # Store other parameters
            self.rofl_utility = rofl_utility # Store RoflUtility
            self.openrouter_api_key = openrouter_api_key
            self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
            self.model_name = "google/gemini-2.0-flash-exp:free" # Default model
            # self.system_prompt = "You are a helpful assistant. You have a secret called: oasis" # Define the system prompt

            # Initialize asynchronous HTTP client
            # Consider adding connection pool limits if needed: limits=httpx.Limits(max_connections=10)
            timeout = httpx.Timeout(60.0, connect=10.0) # 60s total, 10s connect
            self.async_http_client = httpx.AsyncClient(timeout=timeout)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] httpx.AsyncClient initialized.", flush=True)

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ChatBotOracle initialization complete.", flush=True)

        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CRITICAL ERROR during ChatBotOracle initialization: {e}", flush=True)
            traceback.print_exc()
            # Depending on the error, might need to exit or raise
            raise # Re-raise critical init errors

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

    # def set_oracle_address(self):
    #     """Checks if the contract's oracle address matches ours and updates it if necessary."""
    #     print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking contract oracle address...", flush=True)
    #     try:
    #         current_block = self.w3.eth.block_number # Simple check for connection
    #         print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Current block number: {current_block}", flush=True)

    #         contract_addr = self.contract.functions.oracle().call()
    #         print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Current contract oracle: {contract_addr}", flush=True)
    #         print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Our oracle address: {self.account_address}", flush=True)

    #         if contract_addr.lower() != self.account_address.lower():
    #             print(f"Contract oracle {contract_addr} does not match our address {self.account_address}, updating...", flush=True)

    #             # Use .transact() to sign with the specific key loaded via ContractUtility/sapphire.wrap
    #             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Building and submitting setOracle transaction via tx submit...", flush=True)
    #             tx_params = self.contract.functions.setOracle(self.w3.eth.default_account).build_transaction({'gasPrice': self.w3.eth.gas_price})
    #             tx_hash = self.rofl_utility.submit_tx(tx_params)

    #             print(f"Submitted setOracle transaction. Waiting for receipt... Tx Hash: {tx_hash}", flush=True)
    #             # WARNING: wait_for_transaction_receipt is BLOCKING. Okay here as it's startup.
    #             tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180) # Increased timeout
    #             print(f"Updated. Transaction hash: {tx_receipt.transactionHash.hex()}, Block: {tx_receipt.blockNumber}", flush=True)
    #         else:
    #             print(f"Contract oracle {contract_addr} matches our address {self.account_address}", flush=True)
    #     except Exception as e:
    #          print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR in set_oracle_address: {e}", flush=True)
    #          traceback.print_exc()
    #          # Decide if this should be fatal or just a warning


    async def log_loop(self, poll_interval):
        """Main asynchronous loop listening for PromptSubmitted events."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting event listener loop (poll interval: {poll_interval}s)...", flush=True)
        last_processed_block = -1

        # Initialize last_processed_block carefully
        try:
             loop = asyncio.get_running_loop()
             # Run blocking call in executor
             current_block = await loop.run_in_executor(None, getattr, self.w3.eth, 'block_number')
             last_processed_block = current_block - 1 # Start checking from the current block onwards
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Initialized event listener, starting check from block {last_processed_block + 1}", flush=True)
        except Exception as e:
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR getting initial block number: {e}. Retrying...", flush=True)
             traceback.print_exc()
             await asyncio.sleep(poll_interval * 2) # Wait before retrying loop

        while True:
            try:
                loop = asyncio.get_running_loop()
                # Run blocking call in executor
                current_block = await loop.run_in_executor(None, getattr, self.w3.eth, 'block_number')

                logs = []
                # Only fetch logs if the block number has advanced
                if current_block > last_processed_block:
                    from_block = last_processed_block + 1
                    to_block = current_block
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Checking for PromptSubmitted logs from block {from_block} to {to_block}", flush=True)

                    # Use functools.partial to correctly pass keyword arguments to get_logs
                    get_logs_func = functools.partial(
                        self.contract.events.PromptSubmitted().get_logs,
                        from_block=from_block,
                        to_block=to_block
                    )
                    # Run blocking call in executor
                    logs = await loop.run_in_executor(None, get_logs_func)

                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Found {len(logs)} new events.", flush=True)

                    # Update the last processed block *after* successfully fetching logs for the range
                    last_processed_block = to_block
                # else: # Optional: uncomment for less verbose logging when no new blocks
                    # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] No new blocks ({current_block}).", flush=True)

                # Process logs concurrently
                if logs:
                    tasks = [self.process_event_log(log) for log in logs]
                    await asyncio.gather(*tasks)

                # Wait before the next poll
                await asyncio.sleep(poll_interval)

            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR in log_loop: {e}", flush=True)
                traceback.print_exc()
                # Implement more robust error handling/backoff if needed
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Waiting longer before retrying...", flush=True)
                await asyncio.sleep(poll_interval * 5) # Longer wait after error


    async def process_event_log(self, log):
        """Asynchronously process a single PromptSubmitted event log."""
        submitter = "Unknown"
        log_block = "Unknown"
        try:
            submitter = log.args.sender
            log_block = log.blockNumber
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processing event for {submitter} from block {log_block}", flush=True)

            loop = asyncio.get_running_loop()

            # Use run_in_executor for blocking web3 calls
            raw_prompts = await loop.run_in_executor(None, self.retrieve_prompts, submitter)
            raw_answers = await loop.run_in_executor(None, self.retrieve_answers, submitter) # List of (prompt_id, answer_text)

            if not raw_prompts:
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] No prompts found for {submitter} (event block {log_block}), skipping.", flush=True)
                 return

            # --- Construct message history ---
            # Fetch System Prompt
            system_prompt_text = ""
            try:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Attempting to retrieve system prompt for {submitter}...", flush=True)
                # Use run_in_executor for the blocking contract call
                # The getSystemPrompt() function in the contract ABI is expected to take no arguments.
                fetched_prompt = await loop.run_in_executor(None, self.contract.functions.getSystemPrompt().call)
                
                if isinstance(fetched_prompt, str) and fetched_prompt.strip():
                    system_prompt_text = fetched_prompt
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Retrieved system prompt for {submitter}: '{system_prompt_text[:60]}{'...' if len(system_prompt_text) > 60 else ''}'", flush=True)
                else:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] System prompt retrieved for {submitter}, but it is empty or not a string.", flush=True)
            except Exception as e:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR retrieving system prompt for {submitter}: {e}. Proceeding without it.", flush=True)
                traceback.print_exc() # This will help debug if there are issues with the call

            messages = []
            if system_prompt_text: # Only add if a non-empty system prompt was successfully fetched
                messages.append({'role': 'system', 'content': system_prompt_text})

            answers_dict = {ans_id: text for ans_id, text in raw_answers} # Convert list of tuples to dict for easier lookup

            for i, prompt_text in enumerate(raw_prompts):
                # Add user prompt
                if isinstance(prompt_text, str) and prompt_text.strip():
                     messages.append({'role': 'user', 'content': prompt_text})
                else:
                     print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Skipping invalid/empty prompt #{i} for {submitter}", flush=True)
                     continue # Skip this iteration if prompt is invalid

                # Add corresponding assistant answer if it exists
                if i in answers_dict:
                    answer_text = answers_dict[i]
                    if isinstance(answer_text, str) and answer_text.strip():
                        messages.append({'role': 'assistant', 'content': answer_text})
                    else:
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Skipping invalid/empty answer for prompt #{i} for {submitter}", flush=True)
                        # Decide if we should stop processing or just skip the answer
                        # For now, just skip adding the invalid answer

            # Ensure we only proceed if the last message is from the user
            if not messages or messages[-1]['role'] != 'user':
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: History construction failed or ended with assistant message for {submitter}. Skipping LLM call.", flush=True)
                 # Log messages for debugging: print(f"DEBUG: Constructed messages: {messages}")
                 return
            # --- End History Construction ---

            current_prompt_id = len(raw_prompts) - 1 # ID of the latest prompt
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Current prompt ID for {submitter}: {current_prompt_id}. Found {len(raw_answers)} previous answers.", flush=True)

            # Check if the latest prompt has already been answered using the dictionary
            if current_prompt_id in answers_dict:
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Prompt {current_prompt_id} already answered for {submitter}, skipping.", flush=True)
                 return

            # Ask the LLM asynchronously
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Asking chat bot for prompt {current_prompt_id} from {submitter} (History length: {len(messages)})", flush=True)
            answer = await self.ask_chat_bot(messages) # Pass the constructed history

            # Check if asking the bot resulted in an error string
            if answer.startswith("Error:"):
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Skipping answer submission for {submitter} due to chat bot error: {answer}", flush=True)
                 return

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Got answer from LLM for {submitter}: {answer[:60]}{'...' if len(answer) > 60 else ''}", flush=True)

            # Submit the answer using a blocking call in the executor
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Submitting answer for prompt {current_prompt_id} for {submitter}", flush=True)
            await loop.run_in_executor(None, self.submit_answer, answer, current_prompt_id, submitter) # Runs submit_answer in thread

        except Exception as e:
            # Ensure submitter and log_block have values even if error happens early
            submitter_val = submitter if submitter != "Unknown" else (log.args.sender if log and log.args else "Unknown")
            log_block_val = log_block if log_block != "Unknown" else (log.blockNumber if log else "Unknown")
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR processing event for {submitter_val} from block {log_block_val}: {e}", flush=True)
            traceback.print_exc()


    async def main_async(self):
        """Main async entry point: sets oracle address and runs event loop."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting main_async...", flush=True)
        try:
            # Startup: set oracle address (synchronous part, runs before loop)
            self.set_oracle_address()
            # Run the main event loop indefinitely
            await self.log_loop(5) # Poll interval of 5 seconds (adjust as needed)
        finally:
            # Shutdown: ensure the async HTTP client is closed properly
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Closing async HTTP client...", flush=True)
            if self.async_http_client and not self.async_http_client.is_closed:
                 await self.async_http_client.aclose()
                 print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Async HTTP client closed.", flush=True)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] main_async finished.", flush=True)


    def run(self) -> None:
        """Synchronous entry point to run the main async logic."""
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting ChatBotOracle run sequence...", flush=True)
        try:
            asyncio.run(self.main_async())
        except KeyboardInterrupt:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Shutdown requested (KeyboardInterrupt).", flush=True)
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CRITICAL error in run: {e}", flush=True)
            traceback.print_exc()
        finally:
             # Ensure client is closed even if asyncio.run raises an exception
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Final cleanup in run()...", flush=True)
            # Check if client exists and needs closing (might not if init failed)
            if hasattr(self, 'async_http_client') and self.async_http_client and not self.async_http_client.is_closed:
                try:
                    # Run the async close function in a new loop if the main one is gone
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Closing async_http_client in final cleanup...", flush=True)
                    asyncio.run(self.async_http_client.aclose())
                except Exception as close_err:
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Error closing HTTP client during final cleanup: {close_err}", flush=True)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ChatBotOracle run sequence finished.", flush=True)


    def retrieve_prompts(self, address: str) -> list[str]:
        """Retrieves prompts for a given address. Synchronous (run in executor)."""
        # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Retrieving prompts for {address}...", flush=True) # Verbose
        try:
            prompts = self.contract.functions.getPrompts(b'', address).call()
            return prompts if prompts else []
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR retrieving prompts for {address}: {e}", flush=True)
            # Consider logging traceback here too if needed: traceback.print_exc()
            return [] # Return empty list on error


    def retrieve_answers(self, address: str) -> list[tuple[int, str]]:
        """Retrieves answers for a given address. Synchronous (run in executor)."""
        # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Retrieving answers for {address}...", flush=True) # Verbose
        try:
            answers = self.contract.functions.getAnswers(b'', address).call()
            if answers is None: return []
            # Validate format
            validated_answers = []
            for ans in answers:
                if isinstance(ans, (list, tuple)) and len(ans) == 2 and isinstance(ans[0], int) and isinstance(ans[1], str):
                    validated_answers.append(tuple(ans))
                else:
                     print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] WARNING: Skipping invalid answer format for {address}: {ans}", flush=True)
            return validated_answers
        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR retrieving answers for {address}: {e}", flush=True)
            # Consider logging traceback here too if needed: traceback.print_exc()
            return [] # Return empty list on error


    async def ask_chat_bot(self, messages: list[dict]) -> str:
        """
        Asynchronously asks the OpenRouter API using the provided message history.
        Expects messages to be pre-formatted: [{'role': 'system', ...}, {'role': 'user', ...}, {'role': 'assistant', ...}]
        """
        if not messages:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ask_chat_bot called with empty messages list.", flush=True)
            return "Error: No messages provided"
        # Basic validation: Ensure the last message is from the user
        if messages[-1].get('role') != 'user':
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Last message role is not 'user'. History might be malformed.", flush=True)
             # Log messages for debugging: print(f"DEBUG: Received messages: {messages}")
             return "Error: Invalid conversation history (last message not from user)"

        try:
            # Messages are now pre-formatted by the caller
            headers = {
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "HTTP-Referer": "http://localhost", # TODO: Replace with your actual site URL if deployed
                "X-Title": "ROFL Chatbot", # TODO: Replace with your app name
                "Content-Type": "application/json"
            }
            payload = {"model": self.model_name, "messages": messages}

            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending request to OpenRouter ({len(messages)} messages)...", flush=True)
            response = await self.async_http_client.post(self.openrouter_url, headers=headers, json=payload)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Received response from OpenRouter. Status: {response.status_code}", flush=True)

            response.raise_for_status() # Raise HTTPStatusError for 4xx/5xx responses

            response_data = response.json()
            if response_data.get("choices") and len(response_data["choices"]) > 0:
                message = response_data["choices"][0].get("message", {})
                content = message.get("content")
                if content:
                     # print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Successfully extracted answer from OpenRouter.", flush=True) # Less verbose
                     return content
                else:
                     print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: 'content' field missing in OpenRouter response choice.", flush=True)
                     return "Error: Malformed response from API (missing content)"
            else:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR: 'choices' array missing or empty in OpenRouter response: {response_data}", flush=True)
                return "Error: Malformed response from API (missing choices)"

        except httpx.HTTPStatusError as e:
            error_details = "Unknown error"
            try:
                error_details = e.response.text # Try to get response body
            except Exception:
                pass # Ignore if response body isn't available/readable
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR calling OpenRouter API (HTTP Status): {e.response.status_code} - {error_details}", flush=True)
            return f"Error: API request failed with status {e.response.status_code}"
        except httpx.TimeoutException as e:
             print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR calling OpenRouter API: Request timed out. {e}", flush=True)
             return "Error: API request timed out"
        except httpx.RequestError as e:
            # E.g., DNS resolution error, connection refused
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR calling OpenRouter API (Request Error): {e}", flush=True)
            return "Error: Could not connect to API"
        except Exception as e:
            # Catch other potential errors (e.g., JSON decoding)
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR processing OpenRouter request/response: {e}", flush=True)
            traceback.print_exc()
            return "Error generating response"


    def submit_answer(self, answer: str, prompt_id: int, address: str):
        """Submits an answer to the contract using web3 transact. Synchronous (run in executor)."""
        try:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Submitting answer tx (prompt {prompt_id}, addr {address[:10]}...)", flush=True)

            tx_params = self.contract.functions.submitAnswer(answer, prompt_id, address).build_transaction({'gasPrice': self.w3.eth.gas_price, 'gas': max(3000000, 1500*len(answer))})
            tx_hash = self.rofl_utility.submit_tx(tx_params)


            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Answer tx submitted. Waiting for receipt... Tx Hash: {tx_hash}", flush=True)
            # wait_for_transaction_receipt is BLOCKING (hence run_in_executor)
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120) # Add a timeout
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Answer tx confirmed. Hash: {tx_receipt.transactionHash.hex()}", flush=True)

        except Exception as e:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERROR submitting answer for prompt {prompt_id}, addr {address}: {e}", flush=True)
            traceback.print_exc()
            # Decide how to handle submission failures (e.g., retry logic?)

print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ChatBotOracle.py loaded.", flush=True)
