import { useEffect, useState } from "react"
import { withTransition } from "~/utils"

export function FadeIn({ children, delay, className }: { children: React.ReactNode, delay: number, className?: string }) {
  const [show, setShow] = useState(false)

  // Reset the show state on mount and unmount, 
  // otherwise it is shared between pages and the transition doesn't work.
  useEffect(() => {
    setShow(false)
    const timer = setTimeout(() => setShow(true), 0); // Delay just enough to allow for a re-render.

    return () => {
      clearTimeout(timer); // Clear the timeout on unmount.
      setShow(false); // Reset state on unmount.
    };
  }, [children, delay, className])
  
  return (
    <div className={withTransition(show, delay, className)}>{children}</div>
  )
}