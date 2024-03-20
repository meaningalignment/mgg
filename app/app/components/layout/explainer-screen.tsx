import { Link } from "@remix-run/react"
import { withTransition as fadeIn } from "~/utils"
import { useEffect, useState } from "react"
import LoadingButton from "../loading-button"
import { ArrowRight } from "lucide-react"
import { FadeIn } from "../fade-in"

type Props = {
  title?: string
  subtitle?: string
  text?: string
  nextUrl: string
  nextText?: string
  children?: React.ReactNode
  onContinue?: () => void
}

function ContinueButton({ onContinue, nextUrl, nextText }: { onContinue?: () => void, nextUrl: string, nextText?: string }) {
  return onContinue ? (
    <LoadingButton iconRight={<ArrowRight className="h-4 w-4 ml-2" />} onClick={onContinue}>
      {nextText ?? "Continue"}
    </LoadingButton>
  ) :
    <Link to={nextUrl}>
      <LoadingButton iconRight={<ArrowRight className="h-4 w-4 ml-2" />}>
        {nextText ?? "Continue"}
      </LoadingButton>
    </Link>

}

export default function ExplainerScreen({ title, subtitle, text, nextUrl, nextText, children, onContinue }: Props) {
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
  }, [title, subtitle, text, nextUrl, nextText, children])

  const paragraphs = text?.split("\n\n").map((p) => p.trim()) || []
  const baseDelay = title && subtitle ? 225 : title || subtitle ? 150 : 75

  return (
    <div className="flex flex-col h-screen w-screen mt-12">
      <div className="flex flex-col items-center space-y-8 py-12 mx-8">
        <div className="flex flex-col items-center space-y-2 max-w-md">
          {title && <h1 className={fadeIn(show, 0, "text-2xl font-semibold text-center")}>{title}</h1>}
          {subtitle && <h2 className={fadeIn(show, 75, "text-md text-gray-700 text-center")}>{subtitle}</h2>}
        </div>

        {paragraphs.map((paragraph, index) => (
          <p key={index} className={fadeIn(show, 75 * index + baseDelay, "max-w-md text-center")}>{paragraph}</p>
        ))}

        {children && <div className={fadeIn(show, 75 * paragraphs.length + baseDelay)}>
          {children}
        </div>}

        <div className={fadeIn(show, 75 * paragraphs.length + baseDelay + (children ? 75 : 0))}>
          <ContinueButton onContinue={onContinue} nextUrl={nextUrl} nextText={nextText} />
        </div>
      </div>
    </div>
  )
}

export function ExplainerScreenSimple({ nextUrl, nextText, nextDelay, children, onContinue }: Omit<Props, "title" | "subtitle" | "text"> & { nextDelay?: number }) {
  return (
    <div className="flex flex-col h-screen w-screen mt-12">
      <div className="flex flex-col items-center space-y-8 py-12 mx-8">

        {children}

        <FadeIn delay={nextDelay ?? 0} className="text-center">
          <ContinueButton onContinue={onContinue} nextUrl={nextUrl} nextText={nextText} />
        </FadeIn>
      </div>
    </div>
  )
}

export function ExplainerScreenWithAlternativeCTA({ nextDelay, children, cta }: { nextDelay?: number, cta: React.ReactNode, children?: React.ReactNode }) {
  return (
    <div className="flex flex-col h-screen w-screen mt-12">
      <div className="flex flex-col items-center space-y-8 py-12 mx-8">

        {children}

        <FadeIn delay={nextDelay ?? 0} className="text-center">
          {cta}
        </FadeIn>
      </div>
    </div>
  )
}
