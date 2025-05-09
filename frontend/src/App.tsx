import { FC } from 'react'
import { Layout } from './components/Layout'
import { createHashRouter, RouterProvider } from 'react-router-dom'
import { HomePage } from './pages/HomePage'
import { AdminPage } from './pages/AdminPage/AdminPage' // Import AdminPage
import { EIP1193ContextProvider } from './providers/EIP1193Provider'
import { Web3ContextProvider } from './providers/Web3Provider'
import { AppStateContextProvider } from './providers/AppStateProvider'
import { ErrorBoundary } from './components/ErrorBoundary'
import { RouterErrorBoundary } from './components/RouterErrorBoundary'
import { createAppKit } from "@reown/appkit/react";
import { EthersAdapter } from "@reown/appkit-adapter-ethers";
import { AppKitNetwork, defineChain, sapphireTestnet } from '@reown/appkit/networks'
import { NETWORKS } from "@oasisprotocol/sapphire-paratime";
import { WalletConnectContextProvider } from "./providers/WalletConnectProvider";

const { DEV, VITE_WALLET_CONNECT_PROJECT_ID } = import.meta.env;

export const sapphireLocalnet = defineChain({
  id: NETWORKS.localnet.chainId,
  caipNetworkId: `eip115:${NETWORKS.localnet.chainId.toString()}` as unknown as `eip155:${string}`,
  chainNamespace: 'eip155',
  name: "Oasis Sapphire Localnet",
  nativeCurrency: { name: "Sapphire Local Rose", symbol: "TEST", decimals: 18 },
  rpcUrls: {
    default: {
      http: [NETWORKS.localnet.defaultGateway],
      //webSocket: ["ws://localhost:8546/ws"],
    },
  },
  testnet: true,
});

const metadata = { //optional
  name: 'DEMO',
  description: 'DEMO',
  url: 'https://example.com',
  icons: ['https://assets.oasis.io/logotypes/favicon.svg']
}

createAppKit({
  adapters: [new EthersAdapter()],
  networks: [
    sapphireTestnet, ...(DEV ? [
    sapphireLocalnet
  ] : [])] as unknown as [AppKitNetwork],
  metadata,
  projectId: VITE_WALLET_CONNECT_PROJECT_ID,
  features: {
    analytics: true,
  },
});

const router = createHashRouter([
  {
    path: '/',
    element: <Layout />,
    errorElement: <RouterErrorBoundary />,
    children: [
      {
        path: '/',
        element: <HomePage />,
      },
      {
        path: '/admin', // New route for AdminPage
        element: <AdminPage />,
      },
      {
        path: '*',
        element: <HomePage />,
      },
    ],
  },
])

export const App: FC = () => {
  return (
    <ErrorBoundary>
      <EIP1193ContextProvider>
        <WalletConnectContextProvider>
        <Web3ContextProvider>
          <AppStateContextProvider>
            <RouterProvider router={router} />
          </AppStateContextProvider>
        </Web3ContextProvider>
        </WalletConnectContextProvider>
      </EIP1193ContextProvider>
    </ErrorBoundary>
  )
}
