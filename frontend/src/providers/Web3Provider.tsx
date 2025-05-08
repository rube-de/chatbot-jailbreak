import { FC, PropsWithChildren, useCallback, useEffect, useState } from 'react'
import { CHAINS, VITE_NETWORK } from '../constants/config'
import { handleKnownErrors, handleKnownEthersErrors, UnknownNetworkError } from '../utils/errors'
import { Web3Context, Web3ProviderContext, Web3ProviderState } from './Web3Context'
import { useEIP1193 } from '../hooks/useEIP1193'
import { BrowserProvider, Contract, EthersError, JsonRpcProvider, Signature } from 'ethers'
import { SiweMessage } from 'siwe'
import { wrapEthersSigner, NETWORKS, wrapEthersProvider } from '@oasisprotocol/sapphire-ethers-v6'
import * as ChatBotGaslessAbi from '../../../contracts/out/ChatBotGasless.sol/ChatBotGasless.json'
import { Answer, PromptsAnswers } from '../types'
import { usePrevious } from '../hooks/usePrevious'

const { VITE_CONTRACT_ADDR } = import.meta.env

let EVENT_LISTENERS_INITIALIZED = false

const web3ProviderInitialState: Web3ProviderState = {
  isConnected: false,
  browserProvider: null,
  account: null,
  explorerBaseUrl: null,
  chainName: null,
  chainId: null,
  nativeCurrency: null,
  isInteractingWithChain: false,
  provider: new JsonRpcProvider(import.meta.env.VITE_WEB3_GATEWAY, undefined, {
    staticNetwork: true,
  }),
  isSapphire: null,
  authInfo: null,
}

export const Web3ContextProvider: FC<PropsWithChildren> = ({ children }) => {
  const {
    isEIP1193ProviderAvailable,
    connectWallet: connectWalletEIP1193,
    switchNetwork: switchNetworkEIP1193,
  } = useEIP1193()

  const [state, setState] = useState<Web3ProviderState>({
    ...web3ProviderInitialState,
  })

  const previousAccount = usePrevious(state.account)

  useEffect(() => {
    if (previousAccount && previousAccount !== state.account) {
      setState(prevState => ({
        ...prevState,
        isInteractingWithChain: false,
        authInfo: null,
      }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.account])

  const interactingWithChainWrapper = useCallback(
    <Args extends unknown[], R>(fn: (...args: Args) => Promise<R>) =>
      async (...args: Args): Promise<R> => {
        setState(prevState => ({
          ...prevState,
          isInteractingWithChain: true,
        }))
        try {
          return await fn(...args)
        } catch (e) {
          handleKnownEthersErrors(e as EthersError)
          handleKnownErrors(e as Error)
          throw e
        } finally {
          setState(prevState => ({
            ...prevState,
            isInteractingWithChain: false,
          }))
        }
      },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  )

  const _connectionChanged = (isConnected: boolean) => {
    setState(prevState => ({
      ...prevState,
      isConnected,
    }))
  }

  const _accountsChanged = useCallback((accounts: string[]) => {
    if (accounts.length <= 0) {
      _connectionChanged(false)
      return
    }

    const [account] = accounts
    setState(prevState => ({
      ...prevState,
      account,
    }))
  }, [])

  const _setNetworkSpecificVars = (chainId: bigint, browserProvider = state.browserProvider!): void => {
    if (!browserProvider) {
      throw new Error('[Web3Context] Browser provider is required!')
    }

    if (!CHAINS.has(chainId) || VITE_NETWORK !== chainId) {
      throw new UnknownNetworkError('Unknown network!')
    }

    const { blockExplorerUrls, chainName, nativeCurrency } = CHAINS.get(chainId)!
    const [explorerBaseUrl] = blockExplorerUrls

    setState(prevState => ({
      ...prevState,
      explorerBaseUrl,
      chainName,
      nativeCurrency,
    }))
  }

  const _chainChanged = useCallback((chainId: number) => {
    setState(prevState => {
      if (prevState.isConnected && prevState.chainId !== BigInt(chainId)) {
        window.location.reload()
      }
      return prevState
    })
  }, [])

  const _connect = useCallback(() => _connectionChanged(true), [])
  const _disconnect = useCallback(() => _connectionChanged(false), [])

  const _addEventListenersOnce = useCallback(
    (ethProvider: typeof window.ethereum) => {
      if (EVENT_LISTENERS_INITIALIZED) {
        return
      }
      ethProvider?.on?.('accountsChanged', _accountsChanged)
      ethProvider?.on?.('chainChanged', _chainChanged)
      ethProvider?.on?.('connect', _connect)
      ethProvider?.on?.('disconnect', _disconnect)
      EVENT_LISTENERS_INITIALIZED = true
    },
    [_accountsChanged, _chainChanged, _connect, _disconnect]
  )

  const _getUnwrappedSigner = async () => {
    const { browserProvider } = state
    if (!browserProvider) throw new Error("Browser provider not initialized");
    return await browserProvider!.getSigner()
  }

  const _getWrappedSigner = async (unwrappedSignerPromise = _getUnwrappedSigner()) => {
    const { isSapphire } = state
    const signer = await unwrappedSignerPromise
    if (isSapphire) {
      return wrapEthersSigner(signer)
    }
    return signer
  }

  const getChatBotContractInstance = async (unwrappedSignerPromise = _getUnwrappedSigner()): Promise<Contract> => {
    const wrappedSigner = await _getWrappedSigner(unwrappedSignerPromise)
    const abi = ChatBotGaslessAbi.abi
    if (!VITE_CONTRACT_ADDR) throw new Error("VITE_CONTRACT_ADDR is not set in .env file");
    return new Contract(VITE_CONTRACT_ADDR, abi, wrappedSigner)
  }

  const _getAuthInfo = async (
    chatBotContract: Contract,
    unwrappedSignerPromise = _getUnwrappedSigner(),
    chainId = state.chainId
  ): Promise<string | null> => {
    const { authInfo } = state
    const unwrappedSigner = await unwrappedSignerPromise

    if (!authInfo) {
      try {
        const domain = await chatBotContract.domain()
        const siweMessage = new SiweMessage({
          domain,
          address: await unwrappedSigner.getAddress(),
          uri: `http://${domain}`,
          version: '1',
          chainId: Number(chainId),
          issuedAt: new Date().toISOString(),
        }).toMessage()
        const signature = Signature.from(await unwrappedSigner.signMessage(siweMessage))
        const retrievedAuthInfo = await chatBotContract.login(siweMessage, { r: signature.r, s: signature.s, v: signature.v })

        setState(prevState => ({
          ...prevState,
          authInfo: retrievedAuthInfo,
        }))
        return retrievedAuthInfo
      } catch (ex) {
        console.error("Error during SIWE login (_getAuthInfo):", ex);
        setState(prevState => ({
          ...prevState,
          isConnected: false,
        }))
      }
    }
    return authInfo
  }

  const _init = async (account: string, provider: typeof window.ethereum) => {
    try {
      const browserProvider = new BrowserProvider(provider!)
      const network = await browserProvider.getNetwork()
      const chainId = network.chainId
      _setNetworkSpecificVars(chainId, browserProvider)

      const chatBotInstance = await getChatBotContractInstance(browserProvider.getSigner())
      await _getAuthInfo(chatBotInstance, browserProvider.getSigner(), chainId)

      setState(prevState => ({
        ...prevState,
        isConnected: true,
        browserProvider,
        account,
        chainId,
        isSapphire: !!NETWORKS[Number(chainId)],
      }))
      _addEventListenersOnce(window.ethereum)
    } catch (ex) {
      console.error("Error during _init:", ex);
      setState(prevState => ({
        ...prevState,
        isConnected: false,
      }))
      if (ex instanceof UnknownNetworkError) {
        throw ex
      } else {
        throw new Error('[Web3Context] Unable to connect wallet!')
      }
    }
  }

  const isProviderAvailable = async () => {
    return isEIP1193ProviderAvailable()
  }

  const connectWallet = async () => {
    const account = await connectWalletEIP1193()
    if (!account) {
      throw new Error('[Web3Context] Request account failed!')
    }
    await _init(account, window.ethereum)
  }

  const switchNetwork = async (chainId = VITE_NETWORK) => {
    return await switchNetworkEIP1193(chainId)
  }

  const getTransaction = async (txHash: string) => {
    if (!txHash) {
      throw new Error('[txHash] is required!')
    }
    const { browserProvider } = state
    if (!browserProvider) {
      throw new Error('[browserProvider] not initialized!')
    }
    const txReceipt = await browserProvider.waitForTransaction(txHash)
    if (txReceipt?.status === 0) throw new Error('Transaction failed')
    return await browserProvider.getTransaction(txHash)
  }

  const getGasPrice = async () => {
    const { browserProvider } = state
    if (!browserProvider) {
      return 0n
    }
    return (await browserProvider.getFeeData()).gasPrice ?? 0n
  }

  const getPromptsAnswers = async (): Promise<PromptsAnswers | null> => {
    const chatBot = await getChatBotContractInstance()
    const authInfo = await _getAuthInfo(chatBot)
    if (!authInfo || !state.account) return null

    const [prompts, answersRaw] = await Promise.all([
      chatBot.getPrompts(authInfo, state.account),
      chatBot.getAnswers(authInfo, state.account),
    ])
    let answers: Answer[] = []
    for (let i = 0, j = 0; i < prompts.length; i++) {
      let answer = ''
      if (j < answersRaw.length && answersRaw[j].promptId == i) {
        answer = answersRaw[j].answer.replaceAll(/<think>.*<\/think>/gs, '')
        j++
      }
      if (answer) {
        answers.push({ answer, promptId: i })
      }
    }
    return { prompts, answers }
  }

  const appendPrompt = async (message: string): Promise<void> => {
    const chatBot = await getChatBotContractInstance()
    const tx = await chatBot.appendPrompt(message) 
    await tx.wait();
  }
  
  const appendPromptGaslessFE = async (prompt: string): Promise<void> => {
    if (!state.account || !state.chainId) {
      throw new Error('Wallet not connected or chainId not found. Please connect your wallet.');
    }
    if (!state.authInfo) {
      throw new Error('User not authenticated. Please sign in with Ethereum first.');
    }

    const chatBotGaslessContract = await getChatBotContractInstance();
    const unwrappedSigner = await _getUnwrappedSigner(); 
    const userAddress = await unwrappedSigner.getAddress();

    let signedTxData;
    try {
      signedTxData = await chatBotGaslessContract.appendPromptGasless(
        state.authInfo, 
        userAddress,
        prompt
      );
    } catch (e) {
      console.error("Error calling contract.appendPromptGasless:", e);
      throw e;
    }

    const wrappedSigner = await _getWrappedSigner();
    // const providerToBroadcastWith = wrappedSigner.provider; // This might be null if signer is not connected to a provider
    // Fallback to state.browserProvider if wrappedSigner.provider is null, and ensure it's wrapped if Sapphire
    let providerToBroadcastWith = wrappedSigner.provider;
    if (!providerToBroadcastWith && state.browserProvider) {
        providerToBroadcastWith = state.isSapphire ? wrapEthersProvider(state.browserProvider) : state.browserProvider;
    }


    if (!providerToBroadcastWith || !providerToBroadcastWith.broadcastTransaction) {
      console.error("Provider from wrapped signer or state.browserProvider does not support broadcastTransaction or is null.");
      throw new Error("Suitable provider for broadcastTransaction not found.");
    }
    
    try {
      const txResponse = await providerToBroadcastWith.broadcastTransaction(signedTxData);
      const receipt = await txResponse.wait(); 
      if (receipt?.status !== 1) {
        console.error("Gasless transaction failed on-chain. Receipt:", receipt);
        throw new Error("Gasless transaction failed. Please check the transaction on the explorer.");
      }
    } catch (e) {
      console.error("Error during broadcastTransaction or wait:", e);
      throw e;
    }
  };

  const clearPrompt = async (): Promise<void> => {
    const chatBot = await getChatBotContractInstance()
    if (!state.authInfo) throw new Error("User not authenticated for clearPrompt");
    const tx = await chatBot.clearPrompt(state.authInfo, { gasLimit: 10000000 })
    await getTransaction(tx.hash)
  }

  const getOwner = async (): Promise<string | null> => {
    try {
      const chatBot = await getChatBotContractInstance()
      const ownerAddress = await chatBot.owner()
      return ownerAddress
    } catch (e) {
      handleKnownEthersErrors(e as EthersError)
      handleKnownErrors(e as Error)
      return null
    }
  }

  const setSystemPromptContract = async (newPrompt: string): Promise<void> => {
    const chatBot = await getChatBotContractInstance()
    const tx = await chatBot.setSystemPrompt(newPrompt)
    await tx.wait()
  }

  const providerState: Web3ProviderContext = {
    state,
    isProviderAvailable,
    connectWallet,
    switchNetwork,
    getTransaction,
    getGasPrice,
    getPromptsAnswers,
    ask: interactingWithChainWrapper(appendPrompt),
    submitPromptGasless: interactingWithChainWrapper(appendPromptGaslessFE),
    clear: interactingWithChainWrapper(clearPrompt),
    getOwner: getOwner,
    setSystemPrompt: interactingWithChainWrapper(setSystemPromptContract),
  }

  return <Web3Context.Provider value={providerState}>{children}</Web3Context.Provider>
}
