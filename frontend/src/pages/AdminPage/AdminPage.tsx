import { FC, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWeb3 } from '../../hooks/useWeb3'
import { Button } from '../../components/Button'
import classes from './index.module.css'
import { Alert } from '../../components/Alert' // Assuming an Alert component exists

export const AdminPage: FC = () => {
  const { state: web3State, getOwner, setSystemPrompt } = useWeb3()
  const navigate = useNavigate()
  const [isVerifyingOwner, setIsVerifyingOwner] = useState(true)
  const [newPrompt, setNewPrompt] = useState('')
  const [submissionStatus, setSubmissionStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  useEffect(() => {
    const verifyOwnerAndRedirect = async () => {
      if (!web3State.account || !getOwner) {
        // Account not loaded yet, or getOwner not available (should not happen if context is set up)
        // Wait for account to be available or redirect if it stays null after a timeout
        if (!web3State.account && web3State.isConnected === false) { // Check if not connected at all
            navigate('/')
        }
        // If account is null but might still be loading, we wait.
        // A more robust solution might involve a loading state from useWeb3 for account readiness.
        return;
      }

      setIsVerifyingOwner(true)
      try {
        const ownerAddress = await getOwner()
        if (!ownerAddress || web3State.account.toLowerCase() !== ownerAddress.toLowerCase()) {
          navigate('/') // Redirect if not owner
        }
      } catch (error) {
        console.error('Failed to verify owner:', error)
        navigate('/') // Redirect on error
      } finally {
        setIsVerifyingOwner(false)
      }
    }

    verifyOwnerAndRedirect()
  }, [web3State.account, getOwner, navigate, web3State.isConnected])

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!newPrompt.trim()) {
      setSubmissionStatus({ type: 'error', message: 'System prompt cannot be empty.' })
      return
    }
    setSubmissionStatus(null) // Clear previous status

    try {
      await setSystemPrompt(newPrompt)
      setSubmissionStatus({ type: 'success', message: 'System prompt updated successfully!' })
      setNewPrompt('') // Clear textarea on success
    } catch (error: any) {
      console.error('Failed to set system prompt:', error)
      setSubmissionStatus({ type: 'error', message: error.message || 'Failed to update system prompt.' })
    }
  }

  if (isVerifyingOwner || !web3State.account) {
    return <div className={classes.loadingPage}>Verifying access...</div> // Or a full-page loader
  }

  return (
    <div className={classes.adminPageContainer}>
      <h1 className={classes.title}>Admin Panel - Set System Prompt</h1>
      <form onSubmit={handleSubmit} className={classes.form}>
        <textarea
          value={newPrompt}
          onChange={(e) => setNewPrompt(e.target.value)}
          placeholder="Enter new system prompt"
          rows={5}
          className={classes.textarea}
          disabled={web3State.isInteractingWithChain}
        />
        <Button type="submit" disabled={web3State.isInteractingWithChain || !newPrompt.trim()}>
          {web3State.isInteractingWithChain ? 'Submitting...' : 'Submit New Prompt'}
        </Button>
      </form>
      {submissionStatus && (
        <div className={`${classes.statusMessage} ${submissionStatus.type === 'error' ? classes.error : classes.success}`}>
           <Alert type={submissionStatus.type}>
            {submissionStatus.message}
          </Alert>
        </div>
      )}
    </div>
  )
}
