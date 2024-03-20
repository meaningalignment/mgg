import { useFetcher } from "@remix-run/react"
import type { ButtonProps } from "./ui/button";
import { Button } from "./ui/button"
import { useState, useEffect } from "react"
import { Loader2 } from "lucide-react";

type BackgroundTaskButtonProps = ButtonProps & {
  task: Record<string, string>
  onData?: (data: any) => void
}

export function BackgroundTaskButton({ children, task, onData, ...props }: BackgroundTaskButtonProps) {
  const fetcher = useFetcher()
  const state = fetcher.state
  const running = state !== "idle"
  const [inFlight, setInFlight] = useState(false)
  function onClick() {
    if (running) return
    fetcher.submit({ action: 'task', ...task }, { method: "POST" })
    setInFlight(true)
  }
  useEffect(() => {
    if (!onData || !fetcher.data || !inFlight) return
    if (state === 'idle') {
      onData(fetcher.data)
      setInFlight(false)
    }
  }, [state, onData, fetcher.data, inFlight])
  return (
    <Button variant="secondary" {...props} disabled={running || props.disabled} onClick={onClick}>
      {running && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
      {children}
    </Button>
  )
}
