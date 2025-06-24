import { FC, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useWeb3 } from '../../hooks/useWeb3'
import classes from './index.module.css'
import { Button } from '../Button' // Assuming a Button component exists

export const AdminButton: FC = () => {
  const { state: web3State, getOwner } = useWeb3()
  const [isOwner, setIsOwner] = useState(false)
  // Start with isLoading as true only if account is not yet available.
  const [isLoading, setIsLoading] = useState(!web3State.account);

  useEffect(() => {
    // Ensure getOwner is defined before proceeding
    if (!getOwner) {
      // console.log('[AdminButton] getOwner is not available yet.');
      setIsLoading(false); // Can't do anything if getOwner isn't there
      return;
    }

    const checkOwner = async () => {
      // console.log('[AdminButton] checkOwner called. web3State.account:', web3State.account);
      if (web3State.account) {
        // setIsLoading(true); // Re-enable to show loading during async owner check
        try {
          const ownerAddress = await getOwner();
          // console.log('[AdminButton] ownerAddress from getOwner():', ownerAddress);
          if (ownerAddress) { // Ensure ownerAddress is not null
            const isMatch = web3State.account.toLowerCase() === ownerAddress.toLowerCase();
            // console.log('[AdminButton] Comparison:', web3State.account.toLowerCase(), '===', ownerAddress.toLowerCase(), 'Result:', isMatch);
            setIsOwner(isMatch);
          } else {
            // console.log('[AdminButton] ownerAddress is null. Setting isOwner to false.');
            setIsOwner(false);
          }
        } catch (error) {
          // console.error('[AdminButton] Failed to get owner:', error);
          setIsOwner(false);
        } finally {
          // Only set isLoading to false after the check is complete
          setIsLoading(false);
          // console.log('[AdminButton] Finally block. isLoading set to false.');
        }
      } else {
        // Account is not available
        // console.log('[AdminButton] web3State.account is falsy. Setting isOwner to false, isLoading to false.');
        setIsOwner(false);
        setIsLoading(false);
      }
    };

    checkOwner();
  }, [web3State.account, getOwner]); // getOwner added as dependency

  // Log state before returning
  // console.log('[AdminButton] Rendering. isLoading:', isLoading, 'isOwner:', isOwner);

  if (isLoading) {
    return <div className={classes.loading}>Loading...</div>; // Or a spinner component
  }

  if (!isOwner) {
    return null // Don't render anything if not owner or still loading account
  }

  return (
    <Link to="/admin" className={classes.adminButtonLink}>
      <Button variant="outline">Admin</Button>
    </Link>
  )
}
