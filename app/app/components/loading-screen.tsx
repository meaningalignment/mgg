import { withTransition as fadeIn } from "~/utils"
import { useEffect, useState } from "react"
import { Loader2 } from "lucide-react"

type Props = {
  title?: string
  subtitle?: string
}

export default function LoadingScreen({ title, subtitle  }: Props) {
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
  }, [title, subtitle])


  return (
    <div className="flex flex-col h-screen w-screen mt-12">
      <div className="flex flex-col items-center space-y-8 py-12 mx-8">
        {title && <h1 className={fadeIn(show, 0, "text-2xl font-semibold text-center")}>{title}</h1>}
        {subtitle && <h2 className={fadeIn(show, 75, "text-md text-gray-700 text-center animate-pulse mb-8")}>{subtitle}</h2>}
        <Loader2 className={fadeIn(show, 125, "animate-spin h-8 w-8")} />
      </div>
    </div>
  )
}