import { type Message } from "ai"

import { Separator } from "../ui/separator"
import { ChatMessage } from "./chat-message"
import ChatValuesCard from "./chat-values-card"
import type { ValuesCardData } from "~/lib/consts"
import { Button } from "../ui/button"
import ChatMessageLoading from "./chat-message-loading"

export interface ChatList {
  chatId: string,
  messages: Message[]
  valueCards: { position: number; card: ValuesCardData }[]
  onManualSubmit: (card: ValuesCardData) => void
  isFinished: boolean
  isLoading: boolean
}

export function ChatList({
  chatId,
  messages,
  valueCards,
  onManualSubmit,
  isFinished,
  isLoading,
}: ChatList) {
  if (!messages.length) {
    return null
  }

  const valueCard = (index: number) => {
    return valueCards.find((card) => card.position === index)
  }

  return (
    <div className="relative mx-auto max-w-2xl px-4">
      {messages.map((message, index) => (
        <div key={index}>
          {valueCard(index) && (
            <ChatValuesCard
              card={valueCard(index)!.card}
              isFinished={isFinished}
            />
          )}
          <ChatMessage message={message} />
          {index < messages.length - 1 && (
            <Separator className="my-4 md:my-8" />
          )}
        </div>
      ))}
      {!isLoading && valueCard(messages.length - 1) && (
        <Button
          className="relative ml-12 -top-8 md:ml-0 md:-top-0"
          onClick={() => onManualSubmit(valueCard(messages.length - 1)!.card)}
        >
          Submit Card
        </Button>
      )}
      {isLoading && messages[messages.length - 1]?.role === "user" && (
        <>
          <Separator className="my-4 md:my-8" />
          <ChatMessageLoading chatId={chatId} />
        </>
      )}
    </div>
  )
}
