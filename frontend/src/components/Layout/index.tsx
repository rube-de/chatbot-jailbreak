import { FC } from 'react'
import { Outlet, Link } from 'react-router-dom' // Import Link
import classes from './index.module.css'
import { ConnectWallet } from '../ConnectWallet'
import { AdminButton } from '../AdminButton/AdminButton' // Import AdminButton
import { Alert } from '../Alert'
import { useAppState } from '../../hooks/useAppState'
import { Button } from '../Button'
import { StringUtils } from '../../utils/string.utils'
import { LayoutBase } from '../LayoutBase'
import { LogoIcon } from '../icons/LogoIcon'
import { VITE_NETWORK } from '../../constants/config'

export const Layout: FC = () => {
  const {
    state: { appError, isMobileScreen, showFaucetNotification },
    clearAppError,
    setShowFaucetNotification,
  } = useAppState()

  // default state for showFaucetNotification false
  if (VITE_NETWORK === 23293n || VITE_NETWORK === 23295n || VITE_NETWORK === 23294n) {
    setShowFaucetNotification(false)
  }

  return (
    <LayoutBase
      header={
        <>
          {(VITE_NETWORK === 23293n || VITE_NETWORK === 23295n) && showFaucetNotification && (
            <div className={classes.notification}>
              <p>
                Don't have any TEST tokens on Sapphire Testnet? Get some from our{' '}
                <a
                  href="https://faucet.testnet.oasis.io/?paratime=sapphire"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Testnet faucet
                </a>
              </p>

              <button
                className={classes.closeIcon}
                onClick={() => setShowFaucetNotification(false)}
                aria-label="Close notification"
              >
                &times;
              </button>
            </div>
          )}
          <header className={classes.header}>
            <Link to="/" className={classes.logoLink}>
              <LogoIcon />
            </Link>
            <nav className={classes.navigation}>
              <AdminButton />
            </nav>
            <div className={classes.walletSection}>
              <ConnectWallet inline={isMobileScreen} />
            </div>
          </header>
        </>
      }
    >
      <section className={classes.mainSection}>
        {appError && (
          <Alert
            type="error"
            actions={
              <Button variant="text" onClick={clearAppError}>
                &lt; Go back&nbsp;
              </Button>
            }
          >
            {StringUtils.truncate(appError)}
          </Alert>
        )}
        {!appError && <Outlet />}
      </section>
    </LayoutBase>
  )
}
