import type { Message } from "ai"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"

import { cn } from "../../utils"
import { MemoizedReactMarkdown } from "../markdown"
import { IconOpenAI, IconUser } from "../ui/icons"
import { ChatMessageActions } from "./chat-message-actions"
import { Loader2 } from "lucide-react"

export interface ChatMessageProps {
  message: Message
  hideActions?: boolean
}

function MessageContent({ message }: { message: Message }) {
  if (message.role === 'function') {
    return <pre className="text-sm text-neutral-500 whitespace-pre-wrap">{message.content}</pre>
  } else if (message.function_call) {
    return <pre className="text-sm text-neutral-500 whitespace-pre-wrap">{JSON.stringify(message)}</pre>
  } else return (
    <MemoizedReactMarkdown
      className="prose break-words dark:prose-invert prose-p:leading-relaxed prose-pre:p-0"
      remarkPlugins={[remarkGfm, remarkMath]}
      components={{
        p({ children }) {
          return <p className="mb-2 last:mb-0">{children}</p>
        },
      }}
    >
      {message.content}
    </MemoizedReactMarkdown>
  )
}

export function ChatMessage({
  message,
  hideActions,
  ...props
}: ChatMessageProps) {
  return (
    <div
      className={cn("group relative mb-4 flex items-start md:-ml-12")}
      {...props}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow",
          message.role === "user"
            ? "bg-white"
            : "bg-primary text-primary-foreground"
        )}
      >
        {message.role === "user" ? <IconUser /> : <IconOpenAI />}
      </div>
      <div className="ml-4 flex-1 space-y-2 overflow-hidden px-1">
        <MessageContent message={message} />
        {!hideActions && <ChatMessageActions message={message} />}
      </div>
    </div>
  )
}

export function LoadingChatMessage() {
  return (
    <div className={cn("group relative mb-4 flex items-start md:-ml-12")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow bg-primary text-primary-foreground"
        )}
      >
        <IconOpenAI />
      </div>
      <div className="ml-4 flex-1 space-y-2 overflow-hidden px-1">
        <Loader2 className="mt-2 h-4 w-4 animate-spin" />
      </div>
    </div>
  )
}
