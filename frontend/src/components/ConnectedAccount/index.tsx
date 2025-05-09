import { FC } from 'react'
import { JazzIcon } from '../JazzIcon'
import { StringUtils } from '../../utils/string.utils'
import classes from './index.module.css'
import { useAppState } from '../../hooks/useAppState'
import { useAppKit } from "@reown/appkit/react";

interface Props {
  className?: string
  address: string
  chainName: string
}

export const ConnectedAccount: FC<Props> = ({ className, address, chainName }) => {
  const {
    state: { isDesktopScreen },
  } = useAppState()
  const { open } = useAppKit()

  return (
    <button
      className={StringUtils.clsx(className, classes.connectedAccount)}
      onClick={() => {open()}}
    >
      <JazzIcon className={classes.jazzIcon} size={isDesktopScreen ? 30 : 28} address={address} />
      {isDesktopScreen && (
        <p className={classes.connectedAccountDetails}>
          <span className={classes.network}>{chainName}</span>
          <abbr title={address} className={StringUtils.clsx('mono', classes.connectedAccountAddress)}>
            {StringUtils.truncateAddress(address)}
          </abbr>
        </p>
      )}
    </button>
  )
}
