import { FC, PropsWithChildren, useEffect, useRef, useState } from 'react'
import {
  WalletConnectContext,
  WalletConnectProviderContext,
  WalletConnectProviderState,
} from './WalletConnectContext'
import {useAppKit, useDisconnect, useAppKitAccount, useAppKitProvider} from "@reown/appkit/react";

const walletConnectProviderInitialState: WalletConnectProviderState = {}

export const WalletConnectContextProvider: FC<PropsWithChildren> = ({ children }) => {
  const web3ModalAccountState = useAppKitAccount()
  const web3ModalProviderState = useAppKitProvider('eip155')

  const { open } = useAppKit()
  const { disconnect } = useDisconnect()

  const [state] = useState<WalletConnectProviderState>({
    ...walletConnectProviderInitialState,
  })

  const prevChainId = useRef(web3ModalAccountState.caipAddress)

  // Handle chain change
  useEffect(() => {
    if (
      web3ModalAccountState.caipAddress &&
      prevChainId.current &&
      prevChainId.current !== web3ModalAccountState.caipAddress
    ) {
      window.location.reload()
    }

    prevChainId.current = web3ModalAccountState.caipAddress
  }, [web3ModalAccountState.caipAddress])

  const connectWallet = async () => {
    await open()
  }

  const switchAccount = async () => {
    await open({ view: 'Account' })
  }

  const switchNetwork = async () => {
    await open({ view: 'Networks' })
  }

  const disconnectWallet = async () => {
    await disconnect()
  }

  const providerState: WalletConnectProviderContext = {
    state: {
      ...state,
      ...web3ModalAccountState,
      ...web3ModalProviderState,
    },
    connectWallet,
    switchAccount,
    switchNetwork,
    disconnectWallet,
  }

  return <WalletConnectContext.Provider value={providerState}>{children}</WalletConnectContext.Provider>
}