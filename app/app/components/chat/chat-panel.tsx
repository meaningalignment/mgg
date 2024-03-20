import { type UseChatHelpers } from "ai/react"
import { Button } from "../ui/button"
import { PromptForm } from "../prompt-form"
import { ButtonScrollToBottom } from "../button-scroll-to-bottom"
import { IconStop } from "../ui/icons"
import { FooterText } from "../footer"

export interface ChatPanelProps
  extends Pick<
    UseChatHelpers,
    | "append"
    | "isLoading"
    | "reload"
    | "messages"
    | "stop"
    | "input"
    | "setInput"
  > {
  id?: string
  isFinished?: boolean
  collectionId: number | null
}

export function ChatPanel({
  id,
  isLoading,
  isFinished,
  stop,
  append,
  input,
  setInput,
  collectionId
}: ChatPanelProps) {
  return (
    <div className="fixed inset-x-0 bottom-0 light:bg-gradient-to-b from-muted/10 from-10% to-muted/30 to-50%">
      <ButtonScrollToBottom />
      <div className="mx-auto sm:max-w-2xl sm:px-4">
        <div className="flex mb-2 h-10 items-center justify-center">
          {isLoading ? (
            <Button
              variant="outline"
              onClick={() => stop()}
              className="bg-white dark:bg-black"
            >
              <IconStop className="mr-2" />
              Stop generating
            </Button>
          ) : null}
        </div>
        <div className="space-y-4 border-t bg-white px-4 py-2 shadow-lg sm:rounded-t-xl sm:border pb-8 md:py-4">
          <PromptForm
            onSubmit={async (value) => {
              await append({
                id,
                content: value,
                role: "user",
              })
            }}
            input={input}
            setInput={setInput}
            isLoading={isLoading}
            isFinished={isFinished}
            collectionId={collectionId}
          />
          <FooterText className="hidden sm:block" />
        </div>
      </div>
    </div>
  )
}
