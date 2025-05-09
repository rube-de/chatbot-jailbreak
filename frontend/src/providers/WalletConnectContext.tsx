import { createContext } from 'react'
import {useAppKitAccount, useAppKitProvider} from "@reown/appkit/react";

type Web3ModalAccountState = Partial<ReturnType<typeof useAppKitAccount>>
type Web3ModalProviderState = Partial<ReturnType<typeof useAppKitProvider>>
type Web3ModalState = Web3ModalAccountState & Web3ModalProviderState

export interface WalletConnectProviderState extends Web3ModalState {}

export interface WalletConnectProviderContext {
  readonly state: WalletConnectProviderState
  connectWallet: () => Promise<void>
  switchAccount: () => Promise<void>
  switchNetwork: () => Promise<void>
  disconnectWallet: () => Promise<void>
}

export const WalletConnectContext = createContext<WalletConnectProviderContext>(
  {} as WalletConnectProviderContext,
)
